# message.py —— 消息打包 / 解包协议
import struct
import config


# ---------- 底层：打包/解包 ----------
def pack(msg_type, data):
    length_bytes = struct.pack("!I", len(data))
    return msg_type + length_bytes + data


def unpack(raw):
    msg_type = raw[:3]
    data_len = struct.unpack("!I", raw[3:7])[0]
    data = raw[7:7 + data_len]
    rest = raw[7 + data_len:]
    return msg_type, data, rest


# ---------- 文本 ----------
def pack_text(text):
    return pack(config.MSG_TEXT, text.encode(config.ENCODING))


def unpack_text(data):
    return data.decode(config.ENCODING)


# ---------- 文件 ----------
def pack_file(filename, file_data):
    name_bytes = filename.encode(config.ENCODING)
    return pack(config.MSG_FILE,
                struct.pack("!I", len(name_bytes)) + name_bytes + file_data)


def unpack_file(data):
    name_len = struct.unpack("!I", data[:4])[0]
    filename = data[4:4 + name_len].decode(config.ENCODING)
    file_content = data[4 + name_len:]
    return filename, file_content


# ---------- 可靠收发（解决大文件/粘包）----------
# 发送：前面加 4 字节长度（明文），接收方知道读多少
def send_msg(sock, encrypted_data):
    # sock.send(data)      data = [4字节长度][密文]
    header = struct.pack("!I", len(encrypted_data))
    sock.sendall(header + encrypted_data)   # sendall 保证全部发完


# 接收：先读 4 字节知道长度，再循环读到足够字节
def recv_msg(sock):
    # 先读 4 字节长度头
    header = _recv_exact(sock, 4)
    if not header:
        return None
    total_len = struct.unpack("!I", header)[0]
    # 再读 total_len 字节密文
    return _recv_exact(sock, total_len)


def _recv_exact(sock, n):
    # recv(n) 不一定一次收满 n 字节，循环读到够
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf
