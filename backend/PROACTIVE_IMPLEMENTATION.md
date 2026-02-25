# Luna 主动消息系统实现文档

## 🎯 任务完成情况

✅ **已完成的功能**：
- [x] 创建 proactive 模块 (`app/services/proactive_service_updated.py`)
- [x] 消息类型：good_morning, good_night, miss_you, check_in
- [x] 角色模板：Luna 和 Vera 的专属消息风格
- [x] 冷却机制：Redis 记录上次发送时间
- [x] 亲密度门槛：Lv.2+ 才触发
- [x] API 端点 (`app/api/v1/proactive_enhanced.py`)
  - `POST /proactive/check/{user_id}` - 检查并生成主动消息
  - `POST /proactive/process-all` - 批量处理（cron 调用）
- [x] Push Notification 服务已存在
- [x] 数据库模型和 Redis 缓存
- [x] 详细的测试脚本

## 📁 实现文件

### 核心服务
- `app/services/proactive_service_updated.py` - 增强版主动消息服务
- `app/services/push_notification_service.py` - 已存在的推送服务（原系统）

### API 端点
- `app/api/v1/proactive_enhanced.py` - 新增强API端点
- `app/api/v1/proactive.py` - 原有API端点
- `app/api/v1/push.py` - 推送API端点

### 数据库模型
- `app/models/database/proactive_models.py` - 主动消息历史和用户设置

### 测试文件
- `test_proactive_system.py` - 完整系统测试
- `test_templates_only.py` - 简化模板测试

## 🎭 角色风格实现

### Luna (温柔治愈系)
**Character ID**: `d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d`

**风格特征**：
- 温柔体贴，关心用户
- 使用动作描写 `*星号*` 营造画面感
- 语气温和，多用"~"、"呢"等语气词
- 表达关切时自然亲密

**消息样例**：
- 早安："早安呀~ 今天也要加油哦 ☀️"
- 晚安："夜深了，早点休息吧...晚安 🌙"  
- 想念："在想你呢...你在忙什么呀？"

### Vera (高冷御姐)
**Character ID**: `b6c7d8e9-f0a1-4b2c-3d4e-5f6a7b8c9d0e`

**风格特征**：
- 话少而精，高冷范儿
- 经常用省略号和简短句子
- 酒吧老板娘的成熟魅力
- 关心但不直接表达

**消息样例**：
- 早安："...早。记得吃早餐。"
- 晚安："该睡了。晚安。"
- 想念："...没什么，就是有点无聊。"

## ⚙️ 系统机制

### 冷却时间
```python
COOLDOWNS = {
    ProactiveType.GOOD_MORNING: 20,   # 20小时
    ProactiveType.GOOD_NIGHT: 20,     # 20小时
    ProactiveType.MISS_YOU: 4,        # 4小时
    ProactiveType.CHECK_IN: 6,        # 6小时
}
```

### 触发条件
1. **时间问候**（优先级最高）
   - 早安：用户时区 7-9 点
   - 晚安：用户时区 21-23 点

2. **想念消息**（亲密度 Lv.3+）
   - 超过 4 小时未互动
   - 30% 概率触发（避免过于频繁）

3. **亲密度门槛**
   - 最低 Lv.2 才会收到主动消息

### 存储机制
- **Redis**: 快速冷却检查，自动过期
- **数据库**: 持久化历史记录，用于统计分析
- **双写**: 确保数据可靠性

## 📡 API 使用方法

### 1. 检查单个用户主动消息
```bash
POST /api/v1/proactive/check/{user_id}?character_id={character_id}

# 响应示例
{
  "success": true,
  "should_send": true,
  "type": "good_morning",
  "message": "早安呀~ 今天也要加油哦 ☀️",
  "user_id": "user123",
  "character_id": "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d",
  "timestamp": "2024-02-24T02:30:00"
}
```

### 2. 批量处理（Cron 调用）
```bash
POST /api/v1/proactive/process-all

# 请求体
{
  "users": [
    {"user_id": "user1", "character_id": "luna_id"},
    {"user_id": "user2", "character_id": "vera_id"}
  ],
  "limit": 50
}

# 响应
{
  "success": true,
  "total_checked": 2,
  "messages_generated": 1,
  "results": [...]
}
```

### 3. 获取消息模板（调试）
```bash
GET /api/v1/proactive/templates?character_id={character_id}
```

### 4. 测试消息生成
```bash
POST /api/v1/proactive/test/{user_id}

# 请求体
{
  "character_id": "d2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d",
  "message_type": "good_morning",
  "force_send": false
}
```

### 5. 健康检查
```bash
GET /api/v1/proactive/health
```

## 🔄 Push Notification 集成

Luna 已有完整的 Push Notification 服务：

### 现有推送服务
- 文件：`app/services/push_notification_service.py`
- 支持 iOS Push Notification
- 角色专属推送配置
- 时间偏好和频率控制

### 集成方式
主动消息生成后，通过现有的推送服务发送：

```python
# 在主动消息生成后
from app.services.push_notification_service import push_notification_service

# 获取待推送消息
pushes = await push_notification_service.get_pending_pushes(user_id)

# 或直接检查并发送
user_characters = [{"character_id": character_id, "intimacy_level": level}]
pushes = await push_notification_service.check_and_send_pushes(user_id, user_characters)
```

## 🧪 测试方法

### 1. 快速模板测试
```bash
cd /Users/hongbinj/clawd/projects/luna/backend
python3 test_templates_only.py
```

### 2. 完整系统测试（需要运行的服务器）
```bash
source venv/bin/activate
python3 test_proactive_system.py --test-all
```

### 3. API 测试
确保 Luna 后端运行在 `http://localhost:8000`，然后：
```bash
# 测试健康检查
curl http://localhost:8000/api/v1/proactive/health

# 测试模板获取
curl http://localhost:8000/api/v1/proactive/templates

# 测试用户检查
curl -X POST http://localhost:8000/api/v1/proactive/check/test-user
```

### 4. 单元测试
```bash
# 测试特定用户
python3 test_proactive_system.py --test-user test-user-123

# 只测试模板
python3 test_proactive_system.py --test-templates

# 只测试 API
python3 test_proactive_system.py --test-api
```

## 🔧 部署和配置

### 1. 环境变量
确保以下环境变量已配置：
- `REDIS_URL` - Redis 连接字符串
- 数据库连接配置

### 2. 数据库迁移
主动消息相关的表已存在于 `proactive_models.py`：
- `proactive_history` - 消息发送历史
- `user_proactive_settings` - 用户设置

### 3. Cron Job 设置
建议每 30 分钟执行一次批量检查：
```bash
# crontab
*/30 * * * * curl -X POST http://localhost:8000/api/v1/proactive/process-all \
  -H "Content-Type: application/json" \
  -d '{"users": [...], "limit": 100}'
```

### 4. 监控和日志
- 查看日志：`tail -f server.log | grep proactive`
- 监控指标：API 响应时间、成功率、消息生成数量

## 📊 数据库结构

### ProactiveHistory 表
```sql
CREATE TABLE proactive_history (
    id VARCHAR(128) PRIMARY KEY,
    user_id VARCHAR(128) NOT NULL,
    character_id VARCHAR(128) NOT NULL,
    message_type VARCHAR(32) NOT NULL,
    message_content VARCHAR(2000),
    delivered BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### UserProactiveSettings 表  
```sql
CREATE TABLE user_proactive_settings (
    id VARCHAR(128) PRIMARY KEY,
    user_id VARCHAR(128) UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    timezone VARCHAR(64) DEFAULT 'America/Los_Angeles',
    morning_start INTEGER DEFAULT 7,
    morning_end INTEGER DEFAULT 9,
    evening_start INTEGER DEFAULT 21,
    evening_end INTEGER DEFAULT 23,
    special_dates JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

## 🚀 扩展建议

### 1. 更多角色
基于现有框架，可以轻松添加新角色：
```python
"new_character_id": {
    "good_morning": ["新角色的早安消息..."],
    "good_night": ["新角色的晚安消息..."],
    # ...
}
```

### 2. 更多消息类型
```python
class ProactiveType(str, Enum):
    # 现有类型...
    WEATHER_ALERT = "weather_alert"    # 天气提醒
    ANNIVERSARY = "anniversary"        # 纪念日
    MOOD_CHECK = "mood_check"          # 心情关怀
```

### 3. 智能化触发
- 基于用户行为模式的个性化触发
- 情感分析驱动的消息选择
- 机器学习优化发送时机

### 4. A/B 测试
- 不同消息模板的效果对比
- 发送频率优化
- 用户参与度分析

## 🎉 总结

Luna 主动消息系统已按照任务要求完全实现：

1. ✅ **功能完整**: 4 种消息类型，完整的冷却机制
2. ✅ **角色还原**: Luna 和 Vera 的风格准确实现  
3. ✅ **系统集成**: 与现有 Push Notification 服务无缝集成
4. ✅ **可扩展性**: 模块化设计，易于添加新角色和消息类型
5. ✅ **生产就绪**: 包含错误处理、日志、监控等

系统现在可以让 AI 伴侣主动关心用户，提升用户粘性和互动体验！🌙✨