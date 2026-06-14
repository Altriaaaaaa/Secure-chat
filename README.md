# 安全的双向网络聊天程序 —— 项目架构说明

## 项目结构
`
chat/
├── config.py         # 全局配置（端口、密钥、消息类型）
├── crypto_utils.py   # 加密模块（AES-256-CBC）
├── message.py        # 消息协议（打包/解包）
├── server.py         # 服务端（多线程处理连接）
├── client.py         # 客户端（双线程收发）
└── README.md         # 本文件
`

## 数据流
`
用户输入 → pack_text() → pack() → encrypt() → socket.send()
                                                      ↓
                                              socket.recv()
                                                      ↓
屏幕显示 ← unpack_text() ← unpack() ← decrypt()
`

## 依赖安装
`ash
pip install cryptography
`

## 运行方式
`ash
# 终端1：启动服务端
python server.py

# 终端2：启动客户端
python client.py
`

## 验收时老师可能让加的功能 & 应对位置

| 功能              | 改哪个文件         | 怎么改                            |
|-------------------|--------------------|-----------------------------------|
| 换加密算法        | crypto_utils.py    | 新增函数，顶层调用处切换          |
| 文件传输          | message.py         | 加 pack_file/unpack_file          |
|                   | server.py          | 加 elif msg_type == MSG_FILE 分支  |
|                   | client.py          | 加发送文件的命令处理              |
| 用户认证          | message.py         | 加 pack_auth                      |
|                   | server.py          | 加认证分支，校验用户名密码        |
| 心跳保活          | message.py         | 加 pack_heartbeat                 |
|                   | server.py/client.py| 加定时发送心跳的线程              |
| 消息日志          | server.py          | 接收消息后 write 到文件           |
| 群聊/多人         | server.py          | 维护客户端列表，消息广播          |
| 更换端口/密钥     | config.py          | 直接改常量                        |

## 关键设计原则
1. **模块化**：加密、协议、网络三者解耦，各改各的
2. **消息类型前缀**：3字节类型码，扩展只需加 elif 分支
3. **加密透明**：上层只调用 encrypt/decrypt，不关心具体算法
4. **配置集中**：所有可变参数在 config.py，避免硬编码

## TODO 清单（你需要自己写的部分）
- [ ] crypto_utils.py: encrypt() 和 decrypt() 的 AES-CBC 实现
- [ ] message.py: pack() / unpack() / pack_text() / unpack_text()
- [ ] server.py: handle_client() 和 start_server()
- [ ] client.py: recv_loop() 和 start_client()
