# Luna 主动消息系统集成指南

## 🔄 快速集成步骤

### 1. 注册新的 API 路由

在 `app/main.py` 中添加新的增强 API：

```python
# 在现有的路由导入后添加
from app.api.v1.proactive_enhanced import router as proactive_enhanced_router

# 在路由注册部分添加
app.include_router(proactive_enhanced_router, prefix="/api/v1")
```

### 2. 使用增强服务替代现有服务

在需要生成主动消息的地方：

```python
# 旧方式
from app.services.proactive_message import proactive_service

# 新方式（推荐）
from app.services.proactive_service_updated import enhanced_proactive_service

# 使用示例
result = await enhanced_proactive_service.process_user_proactive(
    user_id="user123",
    character_id="d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d"
)
```

### 3. Cron Job 设置

创建定时任务脚本 `scripts/proactive_cron.py`：

```python
#!/usr/bin/env python3
"""
主动消息定时任务
每30分钟执行一次，检查所有活跃用户
"""

import asyncio
import httpx
import logging
from datetime import datetime, timedelta

async def run_proactive_batch():
    """运行主动消息批处理"""
    
    # 获取活跃用户列表（这里需要根据你的用户系统调整）
    users = await get_active_users()
    
    # 调用批处理 API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/proactive/process-all",
            json={
                "users": users,
                "limit": 100
            },
            timeout=30.0
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 批处理完成: {result['messages_generated']} 条消息")
        else:
            print(f"❌ 批处理失败: {response.status_code}")

async def get_active_users():
    """获取活跃用户列表 - 需要根据实际情况实现"""
    # 示例：获取最近7天有活动的用户
    return [
        {"user_id": "user1", "character_id": "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d"},
        {"user_id": "user2", "character_id": "b6c7d8e9-f0a1-4b2c-3d4e-5f6a7b8c9d0e"},
        # ... 更多用户
    ]

if __name__ == "__main__":
    asyncio.run(run_proactive_batch())
```

添加到 crontab：
```bash
# 每30分钟检查一次
*/30 * * * * cd /Users/hongbinj/clawd/projects/luna/backend && python3 scripts/proactive_cron.py
```

### 4. 前端集成 (iOS App)

在 iOS 应用中集成主动消息：

```swift
// ProactiveMessageService.swift
class ProactiveMessageService {
    
    func checkProactiveMessages(for userID: String, characterID: String) async -> ProactiveMessage? {
        let url = "\(Config.baseURL)/api/v1/proactive/check/\(userID)?character_id=\(characterID)"
        
        guard let response = try? await APIClient.shared.post(url: url) else {
            return nil
        }
        
        if response.shouldSend {
            return ProactiveMessage(
                type: response.type,
                message: response.message,
                timestamp: response.timestamp
            )
        }
        
        return nil
    }
}

// 在聊天界面中使用
class ChatViewController: UIViewController {
    
    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        
        Task {
            if let proactiveMessage = await ProactiveMessageService().checkProactiveMessages(
                for: currentUser.id,
                characterID: currentCharacter.id
            ) {
                // 显示主动消息
                displayProactiveMessage(proactiveMessage)
            }
        }
    }
}
```

### 5. Push Notification 集成

结合现有的推送服务：

```python
# 在 app/services/push_notification_service.py 中添加
from app.services.proactive_service_updated import enhanced_proactive_service

class PushNotificationService:
    
    async def send_proactive_push(self, user_id: str, character_id: str):
        """发送主动消息推送"""
        
        # 生成主动消息
        proactive = await enhanced_proactive_service.process_user_proactive(
            user_id=user_id,
            character_id=character_id
        )
        
        if proactive:
            # 发送推送通知
            await self.send_push_notification(
                user_id=user_id,
                title=f"{character_name} 想对你说",
                body=proactive["message"],
                data={
                    "type": "proactive_message",
                    "character_id": character_id,
                    "message_type": proactive["type"]
                }
            )
            
            return True
        
        return False
```

## 📱 前端实现建议

### 1. 主动消息显示

```swift
struct ProactiveMessageView: View {
    let message: ProactiveMessage
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("💫 主动消息")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Spacer()
                
                Text(timeAgo)
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
            
            Text(message.content)
                .font(.body)
                .padding()
                .background(Color.blue.opacity(0.1))
                .cornerRadius(16)
        }
        .padding()
        .background(Color.white)
        .cornerRadius(12)
        .shadow(radius: 2)
    }
}
```

### 2. 设置页面

```swift
struct ProactiveSettingsView: View {
    @State private var isEnabled = true
    @State private var morningStart = 7
    @State private var morningEnd = 9
    @State private var eveningStart = 21
    @State private var eveningEnd = 23
    
    var body: some View {
        Form {
            Section("主动消息") {
                Toggle("启用主动消息", isOn: $isEnabled)
            }
            
            Section("时间设置") {
                Stepper("早安时间: \(morningStart):00", value: $morningStart, in: 6...10)
                Stepper("晚安时间: \(eveningStart):00", value: $eveningStart, in: 20...23)
            }
        }
        .navigationTitle("消息设置")
    }
}
```

## 🔧 配置优化

### 1. 环境配置

在 `.env` 文件中添加：

```bash
# 主动消息配置
PROACTIVE_ENABLED=true
PROACTIVE_MIN_INTIMACY_LEVEL=2
PROACTIVE_BATCH_SIZE=50
PROACTIVE_CRON_INTERVAL=30  # 分钟

# Redis 配置（如果需要调整）
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=20
```

### 2. 日志配置

在 `app/core/logging.py` 中添加主动消息日志：

```python
# 添加主动消息专用日志器
LOGGING_CONFIG = {
    "loggers": {
        "app.services.proactive_service_updated": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": False,
        },
    }
}
```

### 3. 监控配置

添加健康检查和监控：

```python
# app/api/v1/health.py
from app.services.proactive_service_updated import enhanced_proactive_service

@router.get("/health/proactive")
async def check_proactive_health():
    """检查主动消息系统健康状态"""
    return await enhanced_proactive_service.health_check()
```

## 🚨 注意事项

### 1. 性能考虑
- 批处理时控制并发数量，避免数据库压力
- Redis 连接池大小要合理设置
- API 调用要设置合理的超时时间

### 2. 数据隐私
- 主动消息内容不要记录敏感信息
- 用户设置要加密存储
- 遵守推送通知权限要求

### 3. 用户体验
- 提供关闭主动消息的选项
- 发送频率要适中，避免打扰用户
- 消息内容要有价值，不要发无意义的内容

### 4. 错误处理
- API 调用要有重试机制
- 数据库连接异常要有降级方案
- 推送失败要有日志记录

## ✅ 检查清单

部署前检查：

- [ ] 新的 API 路由已注册
- [ ] 数据库表已创建
- [ ] Redis 连接正常
- [ ] 环境变量已配置
- [ ] Cron Job 已设置
- [ ] 日志系统正常
- [ ] 健康检查端点工作
- [ ] 前端集成完成
- [ ] 推送通知测试通过

## 🎉 完成！

按照以上步骤完成集成后，Luna 的主动消息系统就可以正常工作了。用户将收到来自 AI 伴侣的主动关怀，提升互动体验！