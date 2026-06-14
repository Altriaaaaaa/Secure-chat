# 安全聊天系统 —— 功能与实现总览

## 项目结构

```
chat/
├── ws_server.py          # WebSocket 服务端（主程序）
├── web_chat.py            # Flask 前端托管
├── server.py              # TCP 命令行服务端（备用）
├── client.py              # TCP 命令行客户端（备用）
├── crypto_utils.py        # AES 加密模块
├── message.py             # 消息协议模块
├── config.py              # 全局配置
├── templates/
│   └── index.html         # Web 前端页面
├── data/                  # 持久化数据目录
│   ├── users.json
│   ├── history.json
│   └── groups.json
└── requirements.txt
```

---

## 一、加密与安全

| 功能 | 实现 | 关键函数/算法 |
|------|------|--------------|
| 消息加密 | AES-256-CBC | `crypto_utils.py`: `encrypt()`, `decrypt()` |
| 密码哈希 | SHA-256 | `ws_server.py`: `hash_pw()` → `hashlib.sha256()` |
| 传输编码 | Base64 | `base64.b64encode()` / `base64.b64decode()` |
| 块填充 | PKCS7 (128位) | `cryptography.hazmat.primitives.padding.PKCS7` |
| 随机 IV | 每消息独立 16 字节 IV | `os.urandom(16)` |
| 前端加密 | CryptoJS AES-CBC | `CryptoJS.AES.encrypt()` / `CryptoJS.AES.decrypt()` |

**加密流程**：明文 → PKCS7填充 → AES-CBC加密(随机IV) → IV+密文 → Base64 → WebSocket 传输

---

## 二、消息协议

| 功能 | 实现 | 关键函数 |
|------|------|---------|
| 二进制协议 | `[3B类型][4B大端长度][数据]` | `message.py`: `pack()`, `unpack()` |
| 文本消息 | 类型 TAG = `TXT` | `pack_text()`, `unpack_text()` |
| 文件消息 | 类型 TAG = `FIL`，`[文件名长度][文件名][内容]` | `pack_file()`, `unpack_file()` |
| 可靠传输 | 4 字节明文长度前缀 | `send_msg()`, `recv_msg()`, `_recv_exact()` |

---

## 三、用户系统

| 功能 | 实现位置 | 关键逻辑 |
|------|---------|---------|
| 注册 | `ws_server.py` → `t == "register"` | `users[uname] = {"password": hash_pw(pw), ...}` |
| 登录 | `ws_server.py` → `t == "login"` | 比对 SHA-256 哈希，`online[username] = ws` |
| 单点登录 | 重复登录踢旧连接 | `if uname in online: await old_ws.send({"type":"kicked"})` |
| 数据持久化 | JSON 文件存取 | `save_data()` / `load_data()` → `users.json` |

---

## 四、好友系统

| 功能 | 实现 | 数据结构 |
|------|------|---------|
| 添加好友 | 发送请求 → 对方接受 | `users[target]["requests"].append(username)` |
| 接受请求 | 双向写入 friends 列表 | `users[a]["friends"].append(b)` |
| 双向自动添加 | 双方互发请求自动成为好友 | 检查 `username in users[target]["requests"]` |
| 删除好友 | 双向移除 | `users[a]["friends"].remove(b)` |
| 好友验证 | 非好友无法发消息 | `if target not in users[username]["friends"]: error` |

---

## 五、聊天功能

| 功能 | 实现 | 关键函数 |
|------|------|---------|
| 文字消息 | 客户端加密 → 服务端解密查目标 → 重加密转发 | `handle_client` / `ws.onmessage` |
| 文件传输 | 图片内联预览，其他文件下载链接 | `pack_file()`, `renderFile()`, `gm()` MIME 检测 |
| 大文件支持 | WebSocket `max_size=50MB` + `send_msg` 循环读取 | `_recv_exact()` |
| 离线消息 | 服务端暂存，上线推送 | `history[target].append(...)` → login_ok 下发 |
| 消息历史 | 服务端存最近 200 条 / 客户端 localStorage | `history.json`, `localStorage` |

---

## 六、实时体验增强

| 功能 | 实现 | 关键机制 |
|------|------|---------|
| 未读红点 | 好友列表数字气泡 | `unreadCount[from]++`，`selectFriend` 清零 |
| 浏览器通知 | Notification API | `notify()` → `new Notification()` |
| 正在输入 | 打字事件 → WS 中继 → 顶栏显示 | `oninput` → `onTyping()` → `handleTyping()`，2秒节流 |
| 已读回执 | 点开聊天发 read_receipt | `selectFriend` 发送，`handleReadReceipt` 标记 |
| 消息搜索 | 遍历 localStorage 全文匹配 | `searchMsgs()` → 解密比对 `indexOf()` |
| 在线状态 | 好友列表绿点/灰点 | `onlineFriends` 数组，`renderFriends()` 渲染 |

---

## 七、AI 聊天机器人

| 功能 | 实现 | 关键配置 |
|------|------|---------|
| DeepSeek API | OpenAI 兼容格式 | `AI_BASE_URL = "https://api.deepseek.com"` |
| 自动注册 | 启动时创建 `AI-Bot` 用户 | `ensure_bot()` |
| 上下文记忆 | 保留最近 10 轮对话 | `bot_context[username][-10:]` |
| 容错降级 | 未装 aiohttp 返回提示 | `try: import aiohttp ... except ImportError` |

---

## 八、群聊系统

| 功能 | 实现 | 关键逻辑 |
|------|------|---------|
| 创建群 | 任意用户创建 | `groups[name] = {"creator":..., "members":[...], "history":[]}` |
| 添加成员 | 仅群主可加好友入群 | `if username != groups[gname]["creator"]: error` |
| 群消息 | 遍历在线成员转发 | `for m in members: if m!=sender and m in online: send` |
| 群文件 | 同私聊文件协议 | `type: "group_file"`, `renderFile()` |
| 退出群 | 最后一人退出自动删除 | `if len(members) == 0: del groups[gname]` |
| 群历史 | 服务端存 200 条，离线推送 | `group_history` 在 login_ok 下发 |

---

## 九、数据持久化

| 层 | 存储位置 | 内容 |
|----|---------|------|
| 服务端 | `data/users.json` | 用户密码哈希、好友列表、群列表 |
| 服务端 | `data/history.json` | 私聊/群聊消息历史（每人每群最近 200 条） |
| 服务端 | `data/groups.json` | 群成员、群历史 |
| 客户端 | `localStorage` | 当前用户所有聊天记录（key: `chat_用户名`） |

---

## 十、技术栈

| 层 | 技术 |
|----|------|
| 后端语言 | Python 3 |
| 实时通信 | WebSocket (`websockets` 库) |
| 加密库 | `cryptography` (Python), `CryptoJS` (JavaScript) |
| 前端 | 原生 HTML/CSS/JS (无框架) |
| AI API | DeepSeek Chat Completions |
| 哈希 | SHA-256 (`hashlib`) |
| 编码 | Base64, UTF-8 |

---

## 数据流总览

```
发送方浏览器
  │ 用户输入 / 选文件
  ▼
pack_text() / pack_file()     ← message.js
  │ [3B类型][4B长度][数据]
  ▼
encrypt()                      ← CryptoJS AES-256-CBC
  │ IV(16B) + 密文
  ▼
Base64 编码
  │
  ▼ WebSocket
ws_server.py
  │ 解密 → unpack → 查目标
  ├─ 私聊 → 发给 target 的 ws
  ├─ 群聊 → 遍历成员 ws
  └─ AI-Bot → DeepSeek API
  │
  ▼ WebSocket
接收方浏览器
  │ Base64 解码
  ▼
decrypt()                      ← CryptoJS
  │ 明文
  ▼
unpack() → 显示
```