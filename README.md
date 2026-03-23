# WeBot Lite

轻量版微信 AI 聊天机器人，自带 Web 配置面板。微信扫码登录，选模型填 Key，一键启动。

> 基于 [chatgpt-on-wechat](https://github.com/zhayujie/chatgpt-on-wechat) 的微信通道协议，独立实现的轻量版本。无需部署完整项目，单文件即可运行。

## 功能特性

- **微信扫码登录** — 浏览器扫码，无需手机端额外操作
- **11 家模型厂商** — OpenAI / Claude / Gemini / DeepSeek / MiniMax / 智谱GLM / 通义千问 / Kimi / 豆包 / 讯飞星火 / LinkAI
- **多模态消息** — 文本对话、图片识别（视觉模型）、语音转文字
- **联网搜索** — 接入 [Bocha](https://open.bocha.cn) 搜索 API，AI 回复前自动检索最新信息
- **会话记忆** — 按用户维护上下文，支持自定义清除记忆指令
- **Web 配置面板** — 三个 Tab 页管理登录、模型参数、对话模板，实时生效

## 快速开始

### 1. 安装依赖

```bash
pip install flask requests qrcode[pil] pycryptodome
```

### 2. 启动

```bash
python app.py
```

浏览器打开 `http://localhost:5000`

### 3. 使用

1. **模型配置** — 选择 Provider → 选模型 → 填入 API Key → 保存
2. **微信登录** — 点击获取二维码 → 微信扫码确认
3. **启动 Bot** — 点击「启动 Bot」按钮
4. 微信发消息即可收到 AI 回复

## 支持的模型

| Provider | 模型 |
|----------|------|
| **OpenAI** | gpt-5.4, gpt-5.4-mini, gpt-5, gpt-4.1, gpt-4o, gpt-4o-mini, o1 系列 |
| **Claude** | claude-sonnet-4-6, claude-opus-4-6, claude-sonnet-4-5, claude-3-5-sonnet |
| **Gemini** | gemini-3.1-pro-preview, gemini-3.1-flash-lite-preview, gemini-3/2.5/2.0 系列 |
| **DeepSeek** | deepseek-chat (V3), deepseek-reasoner (R1) |
| **MiniMax** | MiniMax-M2.7, M2.5, M2.1, M2 |
| **智谱 GLM** | glm-5-turbo, glm-5, glm-4.7, glm-4-plus, glm-4-flash |
| **通义千问** | qwen3.5-plus, qwen3-max, qwen-max, qwq-plus |
| **Kimi** | kimi-k2.5, kimi-k2, moonshot-v1 系列 |
| **豆包** | doubao-seed-2-0 系列 |
| **讯飞星火** | 4.0Ultra, generalv3.5, max-32k |
| **LinkAI** | linkai-4o, linkai-4o-mini, linkai-3.5 |

所有模型均支持自定义输入，不限于下拉列表。

## 消息处理

| 消息类型 | 处理方式 |
|----------|----------|
| 文本 | 发送给 AI 模型，返回回复 |
| 图片 | 下载解密 → 发送给视觉模型识别（gpt-4o / claude / gemini 等均支持） |
| 语音 | 提取微信自带的转写文本，当文字处理 |
| 文件/视频 | 回复提示「暂不支持」 |

## 联网搜索

在「模型配置」页底部开启，需要 [Bocha](https://open.bocha.cn) API Key（免费注册）。

开启后 Bot 在回复前会自动搜索网络，将搜索结果注入上下文供 AI 参考。

## 配置说明

配置保存在 `config.json`，主要字段：

| 字段 | 说明 |
|------|------|
| `model` | 模型名称 |
| `provider` | 模型厂商（自动设置） |
| `character_desc` | 系统人设 / 角色描述 |
| `temperature` | 生成温度 (0-2) |
| `single_chat_reply_prefix` | 回复前缀 |
| `single_chat_reply_suffix` | 回复后缀 |
| `clear_memory_commands` | 清除记忆指令，JSON 数组 |
| `enable_web_search` | 是否启用联网搜索 |
| `bocha_api_key` | Bocha 搜索 API Key |

## 项目结构

```
bot-config-ui/
├── app.py              # Flask 后端（API + 消息引擎 + AI 调用）
├── config.json         # 运行时配置（自动生成）
└── templates/
    └── index.html      # Web 配置面板
```

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/providers` | GET | 获取所有模型厂商及模型列表 |
| `/api/config` | GET/POST | 读取/保存配置 |
| `/api/weixin/qr` | GET | 获取微信登录二维码 |
| `/api/weixin/qr/poll` | POST | 轮询扫码状态 |
| `/api/weixin/status` | GET | 检查微信登录状态 |
| `/api/bot/start` | POST | 启动消息轮询 |
| `/api/bot/stop` | POST | 停止消息轮询 |
| `/api/bot/status` | GET | Bot 运行状态及统计 |

## 致谢

- [chatgpt-on-wechat](https://github.com/zhayujie/chatgpt-on-wechat) — 微信通道协议及 API 实现参考
- [Bocha Search](https://open.bocha.cn) — 联网搜索 API

## License

MIT
