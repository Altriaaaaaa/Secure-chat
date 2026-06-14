# config.py —— 全局配置，老师验收时可以随便改这里
HOST = "127.0.0.1"      # 服务端监听地址
PORT = 8888             # 服务端端口
BUFFER_SIZE = 4096      # 接收缓冲区大小
ENCODING = "utf-8"      # 字符编码

# ---------- 加密相关 ----------
# 预共享密钥（实际应用中应该通过密钥交换协议协商）
# 这个密钥必须是 16 / 24 / 32 字节（对应 AES-128 / 192 / 256）
PRE_SHARED_KEY = b"this_is_a_32byte_key_for_aes256!"

# ---------- 消息协议 ----------
# 消息类型的前缀，方便扩展（老师加功能时在这里加类型即可）
MSG_TEXT = b"TXT"       # 普通文本消息
MSG_FILE = b"FIL"       # 文件传输（预留）
MSG_AUTH = b"AUT"       # 用户认证（预留）
MSG_HEARTBEAT = b"HTB"  # 心跳（预留）

MSG_TYPE_LEN = 3  # 消息类型占3字节

WS_PORT = 5000          # WebSocket 端口
