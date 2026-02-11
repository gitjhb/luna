
## Telegram Bot 接入方案 (2026-02-10)

**动机：** Telegram 效果不错，可以作为轻量版/获客入口

**优势：**
- 零安装门槛，用户搜 bot 即用
- 消息推送稳定，不用折腾 APNs/FCM
- 支持富文本、图片、语音、贴纸、inline buttons
- 海外用户多，付费意愿强
- 可用 Telegram Stars 支付

**可复用的后端逻辑：**
- 亲密度系统 (intimacy_service)
- 情绪系统 (emotion_service)
- 聊天 API (chat completions)
- 礼物系统
- 约会系统
- 角色设定/prompt

**需要新增：**
- Telegram Bot 网关 (python-telegram-bot / Telethon)
- 用户绑定 (telegram_id ↔ user_id)
- 消息格式适配 (Markdown → Telegram HTML)
- Inline buttons 交互 (送礼物、选项)

**方案：**
- 每个角色一个 bot，或主 bot + /switch 切换
- 轻量体验，重度用户引导下载 App

**优先级：** 待定，可作为 v2.0 获客渠道
