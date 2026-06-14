# 安全双向聊天系统 —— 系统架构与完整文档

## 项目结构

```
chat/
├── config.py              # 全局配置（密钥、端口、消息协议常量）
├── crypto_utils.py        # 加密模块（AES-256-CBC + HMAC-SHA256）
├── message.py             # 消息协议（二进制打包/解包、可靠收发）
├── ws_server.py           # WebSocket 服务端（主程序：用户系统、消息转发、AI Bot）
├── web_chat.py            # Flask 前端托管（提供HTML页面）
├── server.py              # TCP 命令行服务端（备用/演示用）
├── client.py              # TCP 命令行客户端（备用/演示用）
├── requirements.txt       # Python 依赖
├── data/                  # 服务端持久化数据
│   ├── users.json         # 用户账号（密码SHA-256哈希 + 好友列表）
│   ├── history.json       # 聊天历史（每条用户/群聊最近200条）
│   └── groups.json        # 群聊信息（成员、历史）
└── templates/
    └── index.html         # Web 前端（原生 HTML/CSS/JS，CryptoJS 加密）
```

---

## 一、加密安全架构

### 1.1 密钥体系

| 密钥 | 来源 | 用途 | 算法 |
|------|------|------|------|
| `PRE_SHARED_KEY` | `config.py` 硬编码 `b"this_is_a_32byte_key_for_aes256!"` | AES-256 加密/解密 | AES-256-CBC |
| `HMAC_KEY` | `SHA256(PRE_SHARED_KEY + "_hmac_salt")` | 消息签名/验证 | HMAC-SHA256 |
| 密码哈希 | `SHA256(password)` | 登录验证 | SHA-256 |

**密钥派生原理：**
```
PRE_SHARED_KEY ─┬─→ AES-256-CBC 加密密钥（32字节）
                └─→ SHA256(key + "_hmac_salt") ─→ HMAC-SHA256 签名密钥（32字节）
```
加密密钥和签名密钥**同源但不同值**，即使 AES 密钥泄露也无法伪造 HMAC。

### 1.2 加密流程

```
发送方：
  明文 ─→ PKCS7填充 ─→ AES-256-CBC加密(随机IV) ─→ [IV|密文] ─→ HMAC-SHA256签名 ─→ [IV|密文|HMAC(32B)] ─→ Base64

接收方：
  Base64 ─→ [IV|密文|HMAC] ─→ 验证HMAC ─→ 分离IV+密文 ─→ AES-256-CBC解密 ─→ 去PKCS7填充 ─→ 明文
```

### 1.3 安全特性

| 特性 | 实现方式 |
|------|----------|
| 机密性 | AES-256-CBC 加密，每条消息独立随机 IV，相同明文产生不同密文 |
| 完整性 | HMAC-SHA256 签名，篡改1个字节即被检测 |
| 防伪造 | 无 HMAC 密钥者无法生成合法签名，服务器直接拒绝 |
| 密码安全 | SHA-256 哈希存储，数据库泄露也无法还原明文 |
| 登录保护 | 用户名+密码 AES 加密传输，抓包只能看到 Base64 密文 |

---

## 二、消息协议

### 2.1 二进制协议格式

```
[TYPE(3B)][LENGTH(4B 大端)][DATA(变长)]
```

### 2.2 消息类型

| 类型 | 标记 | DATA 格式 |
|------|------|-----------|
| 文本 | `TXT` | UTF-8 编码的文本 |
| 文件 | `FIL` | `[文件名长度(4B)][文件名][文件内容]` |

### 2.3 可靠传输

`send_msg(sock, data)`：发送 `[4B长度头][数据]`，`sendall` 保证完整发送  
`recv_msg(sock)`：先读4B长度头，循环读取直到收满指定字节，解决 TCP 粘包

### 2.4 关键函数

| 函数 | 位置 | 功能 |
|------|------|------|
| `pack(type, data)` | `message.py` | 组装 `[TYPE][LEN][DATA]` |
| `unpack(raw)` | `message.py` | 拆分出 `(type, data, rest)` |
| `pack_text(text)` | `message.py` | 打包文本消息 |
| `unpack_text(data)` | `message.py` | 解包文本消息 |
| `pack_file(name, data)` | `message.py` | 打包文件消息 |
| `unpack_file(data)` | `message.py` | 解包文件消息（返回文件名+内容） |
| `send_msg(sock, data)` | `message.py` | 可靠发送（长度前缀） |
| `recv_msg(sock)` | `message.py` | 可靠接收（循环读取） |

---

## 三、加密模块 (crypto_utils.py)

### 3.1 关键常量

```python
HMAC_KEY = hashlib.sha256(PRE_SHARED_KEY + b"_hmac_salt").digest()
```

### 3.2 关键函数

| 函数 | 输入 | 输出 | 流程 |
|------|------|------|------|
| `encrypt(plaintext)` | 明文字节 | `IV(16B) + 密文 + HMAC(32B)` | 随机IV → PKCS7填充 → AES-CBC加密 → HMAC签名 |
| `decrypt(data)` | 密文+HMAC | 明文字节 | 分离HMAC → 验证签名 → 分离IV → AES-CBC解密 → 去填充 |

---

## 四、WebSocket 服务端 (ws_server.py)

### 4.1 全局变量

| 变量 | 类型 | 用途 |
|------|------|------|
| `users` | `dict` | 用户数据（密码哈希、好友、群组）`{name: {password, friends, requests, groups}}` |
| `online` | `dict` | 在线用户 `{name: ws_connection}` |
| `history` | `dict` | 聊天历史 `{name: [msg, ...]}` |
| `groups` | `dict` | 群聊 `{name: {creator, members, history}}` |
| `bot_context` | `dict` | AI Bot 上下文 `{username: [messages]}` |

### 4.2 配置文件

```python
BOT_NAME = "AI-Bot"
USE_AI = True
AI_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")  # 从环境变量读取
AI_MODEL = "deepseek-chat"
AI_BASE_URL = "https://api.deepseek.com"
```

### 4.3 工具函数

| 函数 | 功能 |
|------|------|
| `hash_pw(pw)` | SHA-256 哈希密码 |
| `save_data()` | 持久化 users/history/groups 到 JSON 文件 |
| `load_data()` | 从 JSON 文件加载数据 |
| `ensure_bot()` | 确保 AI-Bot 账号存在 |
| `broadcast_system(text)` | 向所有在线用户广播系统消息 |

### 4.4 WebSocket 消息处理

`handler(ws)` 根据 `data["type"]` 分发：

| type | 处理函数（内联） | 安全措施 |
|------|-----------------|----------|
| `register` | 解密 payload → 提取用户名密码 → SHA-256 哈希存储 | AES 加密传输 + HMAC 签名 |
| `login` | 解密 payload → SHA-256 哈希比对 → 踢旧连接 → 推送离线消息 | AES 加密传输 + HMAC 签名 |
| `add_friend` | 发送好友请求 / 自动接受双向请求 | 用户名验证 |
| `accept_friend` | 双向添加好友 | 请求验证 |
| `delete_friend` | 双向删除好友 | 好友关系验证 |
| `msg` | **HMAC 验证** → 解密 → 检测文本/文件 → 重加密+签名 → 转发 | HMAC 防伪造 |
| `group_msg` | 解密 → 检测类型 → 重加密 → 广播给群成员 | |
| `create_group` | 创建群聊 | |
| `add_to_group` | 群主添加成员 | 权限验证 |
| `leave_group` | 退出群聊 / 最后一人删除群 | |
| `typing` | 转发输入状态 | |
| `read_receipt` | 转发已读回执 | |

### 4.5 消息转发流程

```
用户A发送 text_msg
  → ws_server 收到 {type:"msg", to:"B", message:"base64密文"}
  → base64解码 → decrypt(密文) HMAC验证
  → unpack → 检测 MSG_TEXT
  → pack_text("B: " + text)
  → encrypt → base64 → 转发给B
  → 存入 history（A记录type:msg, B记录type:msg）

用户A发送 file
  → ws_server 收到 {type:"msg", to:"B", message:"base64密文"}
  → base64解码 → decrypt(密文) HMAC验证
  → unpack → 检测 MSG_FILE
  → 原样密文转发给B {type:"file", message:原密文}
  → 存入 history（A记录type:file, B记录type:file）
```

### 4.6 HMAC 防伪造检查

```python
# 在 if not username 之前执行，未登录者也无法绕过
elif t == "msg":
    encrypted_b64 = data.get("message", "")
    if encrypted_b64:
        try:
            ed = base64.b64decode(encrypted_b64)
            pt = decrypt(ed)  # HMAC 不匹配会抛出 ValueError
        except Exception as e:
            print(f"[SECURITY] Rejected tampered/forged message: {e}")
            await ws.send(json.dumps({
                "type": "error",
                "msg": "HMAC verification failed - message tampered!"
            }))
            continue
    if not username:
        continue
```

---

## 五、前端 (templates/index.html)

### 5.1 加密密钥

```javascript
var KEY = CryptoJS.enc.Utf8.parse("this_is_a_32byte_key_for_aes256!");
var HMAC_KEY = CryptoJS.SHA256("this_is_a_32byte_key_for_aes256!_hmac_salt");
```

### 5.2 加密函数

| 函数 | 功能 | 输出格式 |
|------|------|----------|
| `enc(wa)` | AES-256-CBC 加密 + HMAC 签名 | `[IV(16B)][密文][HMAC(32B)]` (WordArray) |
| `dec(wa)` | HMAC 验证 + AES-256-CBC 解密 | 明文 (WordArray) |
| `pk(t, d)` | 打包消息 `[3B类型][4B长度][数据]` | WordArray |
| `upk(wa)` | 解包消息 | `{type, data}` |
| `u2w(u8)` | `Uint8Array → WordArray` | |
| `w2u(wa)` | `WordArray → Uint8Array` | |
| `pkf(fn, fu)` | 打包文件消息 | WordArray |

### 5.3 UI 渲染函数

| 函数 | 功能 |
|------|------|
| `doAuth()` | 注册/登录：加密发送 `{type, payload}` |
| `showMain(d)` | 登录成功后渲染主界面，加载好友列表和历史 |
| `renderFriends()` | 渲染好友列表（在线绿点、未读红点） |
| `renderGroups()` | 渲染群聊列表 |
| `renderRequests()` | 渲染好友请求 |
| `selectFriend(f)` | 点击好友：合并 localStorage+serverMsgs → 渲染历史 |
| `selectGroup(g)` | 点击群聊：从 localStorage 加载历史 |
| `replayOne(m)` | 渲染单条历史消息（文本解密显示，文件调用 renderFile） |
| `handleMsg(d)` | 收到实时文本消息 → 解密显示 + 存 localStorage |
| `handleFile(d)` | 收到实时文件消息 → 调用 renderFile + 通知 |
| `renderFile(sender,b64,isMe)` | 渲染文件：解密 → 解包 → 图片内联预览 / 下载链接 |
| `stm(t)` | 发送文本消息：加密 → WebSocket |
| `sfm(desc)` | 发送文件消息：加密 → WebSocket |
| `sm()` | 发送入口（文本优先，有文件则发文件） |
| `ofs(inp)` | 文件选择预览 |
| `notify(title,body)` | 浏览器桌面通知 |
| `searchMsgs()` | localStorage 全文搜索 |

### 5.4 localStorage 策略

| 策略 | 说明 |
|------|------|
| 存储内容 | 仅文本消息，跳过文件/图片 |
| 每对话上限 | 50 条（`slice(-50)`） |
| 异常保护 | 所有 `setItem` 包裹 `try/catch`，满则静默跳过 |
| 登录恢复 | 合并 `serverMsgs`（全量含文件）+ `localStorage`（仅文本） |

### 5.5 登录加密流程

```
用户输入 用户名+密码
  → doAuth()
  → CryptoJS.enc.Utf8.parse(JSON.stringify({username, password}))
  → enc() = AES加密 + HMAC签名
  → Base64编码
  → ws.send({type: "register"/"login", payload: "base64密文"})
  → 服务器解密验证
```

---

## 六、Flask 前端托管 (web_chat.py)

| 路由 | 功能 |
|------|------|
| `GET /` | 渲染 `templates/index.html` |
| `POST /send` | （备用HTTP接口）解密 → 文本/文件 → 重加密回复 |

> 注：`web_chat.py` 仅托管 HTML 页面，实时通信通过 `ws_server.py` 的 WebSocket。

---

## 七、数据流向总览

```
浏览器A                     ws_server.py                浏览器B
  │                             │                          │
  ├─ 登录(加密payload) ──────→ │                          │
  │                             ├─ decrypt(HMAC验证)       │
  │                             ├─ SHA256(password) 比对    │
  │  ←────── login_ok ──────── │                          │
  │                             │                          │
  ├─ stm("hello") ──────────→ │                          │
  │  enc(pk("TXT","hello"))   │                          │
  │  HMAC签名                  │                          │
  │                             ├─ decrypt(HMAC验证)       │
  │                             ├─ unpack → MSG_TEXT       │
  │                             ├─ pack_text("A: hello")   │
  │                             ├─ encrypt(HMAC签名)       │
  │                             │ ──── {type:"msg"} ──────→│
  │                             │                          ├─ dec(HMAC验证)
  │                             │                          ├─ 显示"A: hello"
  │                             │                          │
  ├─ sfm(image) ────────────→ │                          │
  │  enc(pkf(name, data))     │                          │
  │  HMAC签名                  │                          │
  │                             ├─ decrypt(HMAC验证)       │
  │                             ├─ unpack → MSG_FILE       │
  │                             │ ──── {type:"file"} ────→│
  │                             │                          ├─ renderFile()
  │                             │                          ├─ 图片内联预览
```

---

## 八、运行方式

```bash
# 安装依赖
pip install -r requirements.txt

# 设置 API Key（可选，用于 AI Bot）
setx DEEPSEEK_API_KEY "sk-your-key"

# 终端1：启动 WebSocket 服务端
python ws_server.py        # ws://127.0.0.1:5000

# 终端2：启动 Web 前端
python web_chat.py          # http://127.0.0.1:5001

# 浏览器打开 http://127.0.0.1:5001
```

---

## 九、验收演示建议

### 9.1 加密验证

1. 发一条消息，F12 → Network → WS → Messages 查看 Base64 密文
2. 搜不到任何明文内容

### 9.2 HMAC 防伪造演示

```javascript
// F12 Console 输入（模拟攻击者）
ws = new WebSocket("ws://127.0.0.1:5000")
ws.onmessage = function(e){ console.log("Server:", e.data) }
ws.onopen = function(){
    ws.send(JSON.stringify({
        type:"msg", to:"user2",
        message:"QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVphYmNkZWZnaGprbG1ub3BxcnN0dXZ3eHl6MDEyMzQ1Njc4OQ==",
        time:Date.now()
    }))
}
// 输出: Server: {"type":"error","msg":"HMAC verification failed - message tampered!"}
```

### 9.3 登录密文验证

F12 → Network → WS → Messages，查看登录消息 `payload` 字段为 Base64 密文，无明文用户名密码。