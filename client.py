# client.py —— 聊天客户端
import socket
import threading
import os
import config
from crypto_utils import encrypt, decrypt
from message import pack_text, unpack_text, pack_file, unpack, recv_msg, send_msg


def recv_loop(sock):
    while True:
        try:
            encrypted_data = recv_msg(sock)
            if not encrypted_data:
                print("\n[!] 服务器断开连接")
                break
            plaintext = decrypt(encrypted_data)
            msg_type, data, _rest = unpack(plaintext)
            if msg_type == config.MSG_TEXT:
                text = unpack_text(data)
                print(f"\n服务端: {text}")
        except Exception as e:
            print(f"\n[!] 连接异常: {e}")
            break


def start_client():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((config.HOST, config.PORT))
    print(f"已连接到 {config.HOST}:{config.PORT}")

    t = threading.Thread(target=recv_loop, args=(sock,), daemon=True)
    t.start()

    print("输入消息发送文本，或输入 /file 图片路径 发送文件（输入 /quit 退出）")
    while True:
        user_input = input(">>> ")
        if user_input.lower() == "/quit":
            break
        if not user_input:
            continue

        if user_input.startswith("/file "):
            filepath = user_input[6:].strip().strip('"')
            if not os.path.exists(filepath):
                print(f"文件不存在: {filepath}")
                continue
            filename = os.path.basename(filepath)
            with open(filepath, "rb") as f:
                file_data = f.read()
            send_msg(sock, encrypt(pack_file(filename, file_data)))
            print(f"[发送文件] {filename} ({len(file_data)} 字节)")
        else:
            send_msg(sock, encrypt(pack_text(user_input)))

    sock.close()
    print("已断开连接")


if __name__ == "__main__":
    start_client()
