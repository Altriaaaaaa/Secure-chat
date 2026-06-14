# web_chat.py —— Web版聊天服务端
from flask import Flask, render_template, request, jsonify
import base64
from crypto_utils import encrypt, decrypt
from message import pack_text, unpack_text, pack_file, unpack_file, unpack
import config

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/send", methods=["POST"])
def send():
    data = request.get_json()
    encrypted_b64 = data.get("message", "")
    encrypted_data = base64.b64decode(encrypted_b64)

    plaintext = decrypt(encrypted_data)
    msg_type, msg_data, _rest = unpack(plaintext)

    # ---------- 文本 ----------
    if msg_type == config.MSG_TEXT:
        text = unpack_text(msg_data)
        print(f"[Web客户端] {text}")
        reply = pack_text(f"服务端收到: {text}")
        encrypted_reply = encrypt(reply)
        reply_b64 = base64.b64encode(encrypted_reply).decode("utf-8")
        return jsonify({"reply": reply_b64})

    # ---------- 文件 ----------
    elif msg_type == config.MSG_FILE:
        filename, file_content = unpack_file(msg_data)
        save_path = f"received_{filename}"
        with open(save_path, "wb") as f:
            f.write(file_content)
        print(f"[Web客户端] 收到文件: {filename} ({len(file_content)} 字节) → {save_path}")

        # 回复：告知客户端文件名和大小
        reply = pack_text(f"文件 {filename} 已收到 ({len(file_content)} 字节)")
        encrypted_reply = encrypt(reply)
        reply_b64 = base64.b64encode(encrypted_reply).decode("utf-8")
        return jsonify({"reply": reply_b64, "file": filename, "size": len(file_content)})

    return jsonify({"reply": ""})


if __name__ == "__main__":
    print(f"Web聊天服务启动: http://127.0.0.1:5001")
    app.run(host="127.0.0.1", port=5001, debug=True)
