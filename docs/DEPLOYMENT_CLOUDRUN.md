# Luna 部署方案 - Cloud Run + Firebase

## 架构概览

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│               (Expo / React Native)              │
└─────────────────┬───────────────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    ▼             ▼             ▼
┌────────┐  ┌──────────┐  ┌──────────────┐
│Firebase│  │ Cloud Run│  │   Firebase   │
│  Auth  │  │ (FastAPI)│  │   Storage    │
└────────┘  └─────┬────┘  └──────────────┘
                  │
         ┌───────┴───────┐
         ▼               ▼
   ┌──────────┐    ┌──────────┐
   │Firestore │    │   LLM    │
   │(用户状态) │    │ (Grok等) │
   └──────────┘    └──────────┘
```

## 服务分工

| 服务 | 用途 | 数据 |
|------|------|------|
| **Cloud Run** | AI 聊天、情感引擎、约会系统 | 无状态 |
| **Firestore** | 用户数据、钱包、订阅状态 | users/{uid}/... |
| **Firebase Auth** | 登录认证 | Apple/Google SSO |
| **Firebase Storage** | 图片存储 | 头像、生成图片 |
| **RevenueCat** | 订阅管理 | Webhook → Cloud Run |

---

## Step 1: Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/

# Set environment
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Run with uvicorn
CMD exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2
```

## Step 2: Cloud Build 配置

```yaml
# cloudbuild.yaml
steps:
  # Build Docker image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - 'gcr.io/$PROJECT_ID/luna-backend:$COMMIT_SHA'
      - '-t'
      - 'gcr.io/$PROJECT_ID/luna-backend:latest'
      - './backend'

  # Push to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - 'gcr.io/$PROJECT_ID/luna-backend:$COMMIT_SHA'

  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'luna-backend'
      - '--image'
      - 'gcr.io/$PROJECT_ID/luna-backend:$COMMIT_SHA'
      - '--region'
      - 'us-west1'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'
      - '--memory'
      - '1Gi'
      - '--cpu'
      - '1'
      - '--min-instances'
      - '0'
      - '--max-instances'
      - '10'
      - '--set-env-vars'
      - 'ENVIRONMENT=production'

images:
  - 'gcr.io/$PROJECT_ID/luna-backend:$COMMIT_SHA'
  - 'gcr.io/$PROJECT_ID/luna-backend:latest'
```

## Step 3: GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]
    paths:
      - 'backend/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - id: auth
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      
      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2
      
      - name: Configure Docker
        run: gcloud auth configure-docker
      
      - name: Build and Push
        run: |
          docker build -t gcr.io/${{ secrets.GCP_PROJECT_ID }}/luna-backend:${{ github.sha }} ./backend
          docker push gcr.io/${{ secrets.GCP_PROJECT_ID }}/luna-backend:${{ github.sha }}
      
      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy luna-backend \
            --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/luna-backend:${{ github.sha }} \
            --region us-west1 \
            --platform managed \
            --allow-unauthenticated \
            --set-secrets "XAI_API_KEY=xai-api-key:latest,OPENAI_API_KEY=openai-api-key:latest"
```

## Step 4: Firestore 数据模型

```
firestore/
├── users/{userId}/
│   ├── profile: { displayName, email, avatar, createdAt }
│   ├── wallet: { totalCredits, dailyFreeCredits, purchasedCredits, bonusCredits }
│   ├── subscription: { tier, expiresAt, productId, willRenew }
│   └── settings: { nsfwEnabled, language, notificationsEnabled }
│
├── users/{userId}/characters/{characterId}/
│   ├── relationship: { intimacyLevel, totalMessages, lastMessageAt }
│   └── memories/: { content, importance, createdAt }
│
└── users/{userId}/transactions/{transactionId}/
    └── { type, amount, productId, createdAt, receipt }
```

## Step 5: 后端 Firebase 集成

```python
# app/services/firebase_service.py
import firebase_admin
from firebase_admin import credentials, firestore, auth

# Initialize Firebase Admin
cred = credentials.Certificate("firebase-credentials.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

class FirebaseUserService:
    """User data operations via Firestore"""
    
    @staticmethod
    async def get_wallet(user_id: str) -> dict:
        doc = db.collection("users").document(user_id).collection("wallet").document("current").get()
        return doc.to_dict() if doc.exists else None
    
    @staticmethod
    async def update_credits(user_id: str, delta: int, reason: str):
        wallet_ref = db.collection("users").document(user_id).collection("wallet").document("current")
        
        @firestore.transactional
        def update_in_transaction(transaction, wallet_ref):
            snapshot = wallet_ref.get(transaction=transaction)
            current = snapshot.to_dict()
            new_total = current["totalCredits"] + delta
            
            if new_total < 0:
                raise ValueError("Insufficient credits")
            
            transaction.update(wallet_ref, {
                "totalCredits": new_total,
                "updatedAt": firestore.SERVER_TIMESTAMP
            })
            return new_total
        
        transaction = db.transaction()
        return update_in_transaction(transaction, wallet_ref)
    
    @staticmethod
    async def set_subscription(user_id: str, tier: str, expires_at: str, product_id: str):
        db.collection("users").document(user_id).update({
            "subscription": {
                "tier": tier,
                "expiresAt": expires_at,
                "productId": product_id,
                "updatedAt": firestore.SERVER_TIMESTAMP
            }
        })
```

## Step 6: 环境变量 (Secret Manager)

```bash
# 创建 secrets
gcloud secrets create xai-api-key --data-file=-
gcloud secrets create openai-api-key --data-file=-
gcloud secrets create revenuecat-webhook-secret --data-file=-
gcloud secrets create firebase-credentials --data-file=firebase-credentials.json

# 授权 Cloud Run 访问
gcloud secrets add-iam-policy-binding xai-api-key \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Step 7: 域名配置

```bash
# 映射自定义域名
gcloud run domain-mappings create \
  --service luna-backend \
  --domain api.luna-app.com \
  --region us-west1

# 会得到 DNS 记录，去域名商配置
```

---

## 部署步骤总结

### 首次部署 (手动)

```bash
# 1. 创建 GCP 项目
gcloud projects create luna-prod --name="Luna Production"
gcloud config set project luna-prod

# 2. 启用 API
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com

# 3. 配置 secrets
gcloud secrets create xai-api-key
echo -n "your-xai-key" | gcloud secrets versions add xai-api-key --data-file=-

# 4. 手动部署测试
cd backend
gcloud run deploy luna-backend \
  --source . \
  --region us-west1 \
  --allow-unauthenticated

# 5. 获取 URL
gcloud run services describe luna-backend --region us-west1 --format='value(status.url)'
```

### 后续部署 (自动)

Push 到 main 分支 → GitHub Actions 自动部署

---

## 费用估算

| 服务 | 免费额度 | 预估月费 (初期) |
|------|----------|-----------------|
| Cloud Run | 200万请求/月 | $0-10 |
| Firestore | 50K 读/20K 写/天 | $0-5 |
| Firebase Auth | 无限 | $0 |
| Firebase Storage | 5GB | $0-1 |
| Secret Manager | 6个免费 | $0 |
| **总计** | | **$0-20/月** |

---

## 待办清单

- [ ] 创建 GCP 项目
- [ ] 启用必要 API
- [ ] 上传 Firebase credentials
- [ ] 配置 Secret Manager
- [ ] 创建 Dockerfile
- [ ] 首次手动部署测试
- [ ] 配置 GitHub Actions
- [ ] 设置自定义域名
- [ ] 迁移数据模型到 Firestore
- [ ] 测试完整流程
