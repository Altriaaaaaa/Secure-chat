# server.py —— 聊天服务端
import socket
import threading
import struct
import config
from crypto_utils import encrypt, decrypt
from message import pack_text, unpack_text, unpack_file, unpack, recv_msg, send_msg


def handle_client(conn, addr):
    print(f"[+] 客户端连接: {addr}")

    while True:
        # recv_msg: 先读4字节长度头,再循环读到足够字节
        encrypted_data = recv_msg(conn)
        if not encrypted_data:
            break

        plaintext = decrypt(encrypted_data)
        msg_type, data, _rest = unpack(plaintext)

        if msg_type == config.MSG_TEXT:
            text = unpack_text(data)
            print(f"[{addr}] {text}")
            reply = pack_text(f"服务端收到: {text}")
            send_msg(conn, encrypt(reply))

        elif msg_type == config.MSG_FILE:
            filename, file_content = unpack_file(data)
            save_path = f"received_{filename}"
            with open(save_path, "wb") as f:
                f.write(file_content)
            print(f"[{addr}] 收到文件: {filename} ({len(file_content)} 字节) → {save_path}")
            reply = pack_text(f"文件 {filename} 已收到 ({len(file_content)} 字节)")
            send_msg(conn, encrypt(reply))

    print(f"[-] 客户端断开: {addr}")
    conn.close()


def start_server():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((config.HOST, config.PORT))
    server_sock.listen(5)
    print(f"服务端启动: {config.HOST}:{config.PORT}，等待连接...")

    while True:
        conn, addr = server_sock.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        t.start()


if __name__ == "__main__":
    start_server()
