# Luna Admin Panel 使用说明

## 🚀 快速开始

### 启动方式
1. **确保 Luna 后端正在运行**：
   ```bash
   cd /Users/hongbinj/clawd/projects/luna/backend
   source venv/bin/activate
   export MOCK_PAYMENT=false
   export MOCK_DATABASE=false
   export ALLOW_GUEST=true
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

2. **打开 Admin Panel**：
   - 直接在浏览器中打开：`file:///Users/hongbinj/clawd/projects/luna/admin-panel/index.html`
   - 或者通过 HTTP 服务器：
     ```bash
     cd /Users/hongbinj/clawd/projects/luna/admin-panel
     python3 -m http.server 8080
     # 然后访问：http://localhost:8080
     ```

## 📊 功能模块

### 1. 概览 Tab（📊）
- **系统统计**：显示总用户数、总会话数、总消息数
- **连接状态**：实时显示与后端的连接状态（绿点=正常，红点=断线）
- **最近活跃用户**：显示最近活跃的5个用户

### 2. 聊天记录 Tab（💬）
- **用户列表**：左侧显示所有用户，可以搜索
- **聊天查看**：点击用户查看其聊天记录
- **消息分页**：支持分页浏览历史消息
- **消息详情**：显示角色、时间戳、token使用量等

### 3. 主动消息 Tab（⏰）
- **消息模板**：查看所有角色的主动消息模板
- **测试工具**：
  - 输入用户 ID 和消息类型
  - **测试发送**：检查是否可以发送（遵守冷却时间）
  - **强制发送**：忽略冷却限制强制发送
- **系统状态**：检查主动消息系统健康状况

**消息类型**：
- 🌅 good_morning：早安消息
- 🌙 good_night：晚安消息
- 👋 check_in：关怀问候
- 💪 mood_boost：心情鼓励
- 🎯 activity_suggestion：活动建议

### 4. 角色管理 Tab（📝）
- **角色列表**：显示所有角色及其状态
- **角色详情**：点击"查看详情"查看完整角色信息
- **角色状态**：显示是否活跃、是否为 Spicy 类型
- **Prompt 查看**：查看角色的系统提示词和个性设置

### 5. 亲密度 Tab（💝）
- **亲密度统计**：显示用户与各角色的亲密度等级和经验值
- **情绪状态**：显示用户对各角色的情绪分数
- **颜色编码**：
  - 🟢 绿色：80-100（非常好）
  - 🔵 蓝色：60-79（良好）
  - 🟡 黄色：40-59（一般）
  - 🟠 橙色：20-39（较差）
  - 🔴 红色：0-19（很差）

## 🛠️ 使用技巧

### 1. 实时数据
- 界面会自动检查连接状态（每30秒）
- 使用"🔄 刷新全部"按钮手动刷新所有数据
- 每个 Tab 都有独立的刷新按钮

### 2. 搜索和筛选
- 聊天记录 Tab 支持按用户 ID 搜索
- 所有表格都支持分页浏览

### 3. 主动消息测试
- 使用真实的用户 ID 进行测试
- "测试发送"会检查冷却时间，"强制发送"会忽略限制
- 测试结果会显示详细的错误或成功信息

### 4. 快捷键
- `Esc`：关闭模态框
- 点击模态框背景：关闭模态框

## 🔗 API 端点

Admin Panel 使用以下 API 端点：

### 统计数据
- `GET /api/v1/admin/stats` - 系统统计

### 用户管理
- `GET /api/v1/admin/users` - 用户列表
- `GET /api/v1/admin/users/{user_id}` - 用户详情

### 会话管理
- `GET /api/v1/admin/sessions` - 会话列表
- `GET /api/v1/admin/sessions/{session_id}/messages` - 消息记录

### 主动消息
- `GET /api/v1/proactive/templates` - 消息模板
- `POST /api/v1/proactive/test/{user_id}` - 测试发送

### 角色管理
- `GET /api/v1/admin/characters` - 角色列表
- `GET /api/v1/admin/characters/{character_id}` - 角色详情

### 亲密度和情绪
- `GET /api/v1/admin/intimacy` - 亲密度数据
- `GET /api/v1/admin/emotions` - 情绪数据

## 🚨 注意事项

1. **本地开发环境**：此 Admin Panel 仅用于本地开发，不需要认证
2. **数据安全**：请勿在生产环境使用此管理界面
3. **后端依赖**：确保 Luna 后端服务正在运行在 `localhost:8000`
4. **浏览器兼容**：推荐使用 Chrome、Firefox 或 Safari 浏览器

## 🎯 常见问题

**Q: 显示"连接失败"怎么办？**
A: 检查 Luna 后端是否在运行：`curl http://localhost:8000/health`

**Q: 主动消息测试失败？**
A: 确保用户 ID 存在，并检查后端日志是否有错误

**Q: 数据不更新？**
A: 点击"🔄 刷新全部"按钮，或者检查浏览器控制台是否有错误

**Q: 模态框无法关闭？**
A: 按 `Esc` 键或点击模态框背景区域

---

**版本**: 1.0.0  
**创建时间**: 2026-02-24  
**技术栈**: HTML + Tailwind CSS + Vanilla JavaScript  
**兼容性**: Luna Backend API v1