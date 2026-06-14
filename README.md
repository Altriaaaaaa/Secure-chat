# 🔐 Secure Chat — 安全双向聊天系统

基于 **AES-256-CBC + HMAC-SHA256** 加密的实时 WebSocket 聊天系统，支持好友系统、群聊、文件传输、AI 机器人。

> 计算机安全和保密技术 · 期末项目

---

## 功能特性

### 加密安全

| 特性 | 实现 |
|------|------|
| 消息加密 | AES-256-CBC，每条消息独立随机 IV |
| 消息签名 | HMAC-SHA256，防篡改、防伪造 |
| 登录保护 | 用户名+密码 AES 加密传输 |
| 密码存储 | SHA-256 哈希，不存明文 |
| 密钥派生 | HMAC 密钥由预共享密钥加盐派生，与 AES 密钥隔离 |

### 通信功能

- 🔄 WebSocket 实时双向通信
- 👥 好友系统（添加/删除/请求验证）
- 👪 群聊（创建/加人/退群）
- 📎 文件传输（图片内联预览）
- 💬 离线消息（上线自动推送）
- ⌨️ 输入状态提示（"typing..."）
- ✅ 已读回执（"Read"）
- 🔔 浏览器桌面通知
- 🔍 消息全文搜索

### 其他

- 🤖 AI 机器人（DeepSeek API）
- 💾 服务端 JSON 持久化

---

## 项目结构

```
chat/
├── ws_server.py          # WebSocket 服务端（主程序）
├── web_chat.py           # Flask 前端托管
├── crypto_utils.py       # 加密模块（AES + HMAC）
├── message.py            # 消息协议（打包/解包）
├── config.py             # 全局配置
├── server.py             # TCP 服务端（备用）
├── client.py             # TCP 客户端（备用）
├── templates/
│   └── index.html        # Web 前端（原生 HTML/CSS/JS）
├── data/                 # 持久化数据目录
├── SYSTEM_ARCHITECTURE.md # 完整架构文档
└── requirements.txt
```

---

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. （可选）设置 AI Bot 的 API Key
# PowerShell:
[Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY", "sk-your-key", "User")

# 3. 启动 WebSocket 服务端
python ws_server.py

# 4. 另开终端，启动 Web 前端
python web_chat.py

# 5. 浏览器打开 http://127.0.0.1:5001
#    注册两个账号，互相添加好友，开始加密聊天
```

---

## 加密流程

```
发送: 明文 → PKCS7填充 → AES-256-CBC(随机IV) → HMAC-SHA256签名 → Base64 → WebSocket
接收: Base64 → HMAC验证 → AES-256-CBC解密 → 去填充 → 明文
```

HMAC 签名保护每条消息的完整性——篡改 1 个字节即被检测，服务器主动拒绝。

---

## 验收演示

详见 `SYSTEM_ARCHITECTURE.md` 第九章，包含：

1. DevTools 查看密文
2. Console 模拟中间人攻击 → HMAC 拒绝
3. 登录加密传输验证