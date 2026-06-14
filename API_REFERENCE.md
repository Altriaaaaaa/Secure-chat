# ============================================================
#  函数速查手册 —— 本项目用到的所有库函数参数说明
# ============================================================

# ============================================
#  一、crypto_utils.py 用到的函数
# ============================================

# 1. os.urandom(n)
#    生成 n 字节的密码学安全随机数
#    参数：n (int) —— 字节数，AES-CBC 的 IV 需要 16
#    返回：bytes
#    示例：iv = os.urandom(16)

# 2. algorithms.AES(key)
#    创建 AES 算法对象
#    参数：key (bytes) —— 密钥，长度必须是 16/24/32（对应 AES-128/192/256）
#    返回：AES 算法对象

# 3. modes.CBC(iv)
#    创建 CBC 模式对象
#    参数：iv (bytes) —— 初始化向量，必须是 16 字节
#    返回：CBC 模式对象

# 4. Cipher(algorithm, mode, backend=...)
#    创建密码器
#    参数：
#        algorithm —— 算法对象（如 algorithms.AES(key)）
#        mode      —— 模式对象（如 modes.CBC(iv)）
#        backend   —— 后端，填 default_backend()
#    返回：Cipher 对象

# 5. cipher.encryptor()
#    创建加密器，无参数
#    返回：加密器对象

# 6. cipher.decryptor()
#    创建解密器，无参数
#    返回：解密器对象

# 7. encryptor.update(data)
#    加密一段数据
#    参数：data (bytes) —— 要加密的数据
#    返回：bytes（密文）

# 8. encryptor.finalize()
#    完成加密，处理最后一块，无参数
#    返回：bytes（最后一块密文，通常为空或填充块）

# 9. decryptor.update(data)
#    解密一段数据
#    参数：data (bytes) —— 密文
#    返回：bytes（明文，含填充）

# 10. decryptor.finalize()
#     完成解密，无参数
#     返回：bytes

# 11. padding.PKCS7(block_size)
#     创建 PKCS7 填充器
#     参数：block_size (int) —— 块大小，单位是位！AES是128位
#     返回：填充器对象
#     例：padding.PKCS7(128)

# 12. padder.update(data)
#     向填充器喂数据
#     参数：data (bytes)
#     返回：bytes（填充后的数据，最后一块之前可能为空）

# 13. padder.finalize()
#     完成填充，返回最后一个填充块，无参数
#     返回：bytes

# 14. unpadder.update(data)
#     向去填充器喂数据
#     参数：data (bytes)
#     返回：bytes

# 15. unpadder.finalize()
#     完成去填充，验证并移除填充，无参数
#     返回：bytes

# 16. default_backend()
#     获取默认加密后端，无参数
#     返回：Backend 对象

# ============================================
#  二、message.py 用到的函数
# ============================================

# 1. struct.pack(format, value)
#    把Python值打包成bytes
#    参数：
#        format (str) —— 格式字符串，"!I" 表示大端4字节无符号整数
#        value  (int) —— 要打包的整数
#    返回：bytes
#    示例：struct.pack("!I", 100) → b'\x00\x00\x00d'

# 2. struct.unpack(format, data)
#    把bytes解包成Python值
#    参数：
#        format (str) —— 格式字符串，"!I" 表示大端4字节无符号整数
#        data   (bytes) —— 要解包的字节（至少4字节）
#    返回：元组，如 (100,)，取 [0]
#    示例：struct.unpack("!I", b'\x00\x00\x00d') → (100,)

# 3. bytes.decode(encoding)
#    bytes → str
#    参数：encoding (str) —— 编码方式，本项目用 "utf-8"
#    返回：str
#    示例：b"hello".decode("utf-8") → "hello"

# 4. str.encode(encoding)
#    str → bytes
#    参数：encoding (str) —— 编码方式，本项目用 "utf-8"
#    返回：bytes
#    示例："hello".encode("utf-8") → b"hello"

# ============================================
#  三、server.py / client.py 用到的函数
# ============================================

# 1. socket.socket(family, type)
#    创建套接字
#    参数：
#        family —— socket.AF_INET（IPv4）
#        type   —— socket.SOCK_STREAM（TCP）
#    返回：socket 对象

# 2. sock.setsockopt(level, optname, value)
#    设置套接字选项
#    参数：
#        level   —— socket.SOL_SOCKET
#        optname —— socket.SO_REUSEADDR（允许端口复用）
#        value   —— 1（开启）
#    无返回值

# 3. sock.bind(address)
#    绑定地址和端口
#    参数：address (tuple) —— (host, port)，如 ("127.0.0.1", 8888)
#    无返回值

# 4. sock.listen(backlog)
#    开始监听
#    参数：backlog (int) —— 最大等待连接数，填 5
#    无返回值

# 5. sock.accept()
#    接受一个客户端连接（阻塞等待）
#    无参数
#    返回：(conn, addr)
#        conn —— 与客户端通信的新 socket
#        addr —— 客户端地址元组 (ip, port)

# 6. sock.connect(address)
#    连接到服务器（客户端用）
#    参数：address (tuple) —— (host, port)
#    无返回值

# 7. conn.send(data)
#    发送数据
#    参数：data (bytes)
#    返回：int（实际发送的字节数）

# 8. conn.recv(bufsize)
#    接收数据
#    参数：bufsize (int) —— 缓冲区大小，用 config.BUFFER_SIZE
#    返回：bytes（收到的数据，连接断开时返回 b"")

# 9. sock.close() / conn.close()
#    关闭套接字，无参数无返回

# 10. threading.Thread(target=函数, args=参数元组, daemon=True)
#     创建线程
#     参数：
#         target —— 线程要执行的函数（不加括号，如 handle_client）
#         args   —— 传给函数的参数，元组形式，如 (conn, addr)
#         daemon —— True 表示守护线程（主线程退出时自动结束）
#     返回：Thread 对象

# 11. thread.start()
#     启动线程，无参数无返回
#     例：t = threading.Thread(...); t.start()

# 12. input(prompt)
#     从键盘读取一行输入
#     参数：prompt (str) —— 提示文字，如 ">>> "
#     返回：str（用户输入，不含末尾换行符）

# 13. print(*objects)
#     打印输出
#     参数：任意多个对象，用逗号隔开即可
#     例：print(f"[{addr}] {text}")
