# ws_server.py -- Secure chat with registration, login, friend system, AI bot, persistence
import asyncio, json, base64, hashlib, os
from websockets.asyncio.server import serve
import config
from crypto_utils import encrypt, decrypt
from message import pack_text, unpack_text, unpack

# ---- Data ----
users = {}
online = {}
history = {}
bot_context = {}
groups = {}
DATA_DIR = "data"

# ---- AI Bot Config ----
BOT_NAME = "AI-Bot"
USE_AI = True
AI_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
AI_MODEL = "deepseek-chat"
AI_BASE_URL = "https://api.deepseek.com"

# ---- Helpers ----
def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def save_data():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(os.path.join(DATA_DIR, "users.json"), "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False)
        trimmed = {k: v[-200:] for k, v in history.items()}
        with open(os.path.join(DATA_DIR, "history.json"), "w", encoding="utf-8") as f:
            json.dump(trimmed, f, ensure_ascii=False)
        with open(os.path.join(DATA_DIR, "groups.json"), "w", encoding="utf-8") as f:
            json.dump(groups, f, ensure_ascii=False)
    except Exception as e:
        print(f"[SAVE] error: {e}")

def load_data():
    global users, history
    try:
        up = os.path.join(DATA_DIR, "users.json")
        hp = os.path.join(DATA_DIR, "history.json")
        if os.path.exists(up):
            with open(up, "r", encoding="utf-8") as f:
                users = json.load(f)
            print(f"[LOAD] {len(users)} users restored")
        if os.path.exists(hp):
            with open(hp, "r", encoding="utf-8") as f:
                history = json.load(f)
            print(f"[LOAD] history restored for {len(history)} users")
        gp = os.path.join(DATA_DIR, "groups.json")
        global groups
        if os.path.exists(gp):
            with open(gp, "r", encoding="utf-8") as f:
                groups = json.load(f)
            print(f"[LOAD] {len(groups)} groups restored")
    except Exception as e:
        print(f"[LOAD] error: {e}")

def ensure_bot():
    if BOT_NAME not in users:
        users[BOT_NAME] = {"password": hash_pw("bot"), "friends": [], "requests": []}
    if BOT_NAME not in history:
        history[BOT_NAME] = []
    print(f"[BOT] {BOT_NAME} ready (USE_AI={USE_AI})")

async def broadcast_system(text, exclude=None):
    dead = []
    for u, uws in list(online.items()):
        if u == exclude:
            continue
        try:
            await uws.send(json.dumps({"type": "system", "msg": text}))
        except:
            dead.append(u)
    for u in dead:
        if u in online:
            del online[u]

# ---- Main Handler ----
async def handler(ws):
    username = None
    try:
        async for raw_msg in ws:
            data = json.loads(raw_msg)
            t = data.get("type")

            # ===== REGISTER =====
            if t == "register":
                try:
                    encrypted = base64.b64decode(data.get("payload", ""))
                    pt = decrypt(encrypted)
                    auth_data = json.loads(pt.decode("utf-8"))
                    uname = auth_data.get("username", "").strip()
                    pw = auth_data.get("password", "")
                except:
                    await ws.send(json.dumps({"type": "error", "msg": "Auth error"}))
                    continue
                if not uname or not pw:
                    await ws.send(json.dumps({"type": "error", "msg": "Username and password required"}))
                    continue
                if uname in users:
                    await ws.send(json.dumps({"type": "error", "msg": "Username already exists"}))
                    continue
                users[uname] = {"password": hash_pw(pw), "friends": [BOT_NAME], "requests": []}
                users[BOT_NAME]["friends"].append(uname)
                history[uname] = []
                save_data()
                print(f"[REG] {uname}")
                await ws.send(json.dumps({"type": "register_ok"}))

            # ===== LOGIN =====
            elif t == "login":
                try:
                    encrypted = base64.b64decode(data.get("payload", ""))
                    pt = decrypt(encrypted)
                    auth_data = json.loads(pt.decode("utf-8"))
                    uname = auth_data.get("username", "").strip()
                    pw = auth_data.get("password", "")
                except:
                    await ws.send(json.dumps({"type": "error", "msg": "Auth error"}))
                    continue
                if uname not in users:
                    await ws.send(json.dumps({"type": "error", "msg": "User not found"}))
                    continue
                if users[uname]["password"] != hash_pw(pw):
                    await ws.send(json.dumps({"type": "error", "msg": "Wrong password"}))
                    continue
                # Kick old session if already online
                if uname in online:
                    try:
                        await online[uname].send(json.dumps({"type":"kicked","msg":"Logged in from another device"}))
                        await online[uname].close()
                    except: pass
                    print(f"[KICK] {uname} old session closed")
                username = uname
                online[username] = ws
                print(f"[+] {username} online")
                await broadcast_system(f"{username} joined", exclude=username)

                if BOT_NAME not in users[username]["friends"]:
                    users[username]["friends"].append(BOT_NAME)
                    users[BOT_NAME]["friends"].append(username)
                    save_data()

                await ws.send(json.dumps({
                    "type": "login_ok",
                    "friends": users[username]["friends"],
                    "requests": users[username]["requests"],
                    "online": [u for u in online if u != username and u in users[username]["friends"]],
                    "groups": users[username].get("groups",[]),
                    "group_info": {g: groups[g].get("members",[]) for g in users[username].get("groups",[]) if g in groups},
                    "history": history.get(username, [])[-20:],
                    "group_history": {g: groups[g].get("history",[])[-20:] for g in users[username].get("groups",[]) if g in groups}
                }))

            # ===== ADD FRIEND =====
            elif t == "add_friend":
                if not username:
                    continue
                target = data.get("username", "").strip()
                if target not in users:
                    await ws.send(json.dumps({"type": "error", "msg": "User not found"}))
                    continue
                if target == username:
                    await ws.send(json.dumps({"type": "error", "msg": "Cannot add yourself"}))
                    continue
                if target in users[username]["friends"]:
                    await ws.send(json.dumps({"type": "error", "msg": "Already friends"}))
                    continue

                # Auto-accept if target already sent request
                if username in users[target].get("requests", []):
                    users[target]["requests"].remove(username)
                    users[target]["friends"].append(username)
                    users[username]["friends"].append(target)
                    save_data()
                    await ws.send(json.dumps({"type": "friend_added", "username": target}))
                    if target in online:
                        await online[target].send(json.dumps({"type": "friend_added", "username": username}))
                else:
                    users[target].setdefault("requests", []).append(username)
                    await ws.send(json.dumps({"type": "request_sent", "username": target}))
                    if target in online:
                        await online[target].send(json.dumps({
                            "type": "friend_request", "from": username,
                            "requests": users[target]["requests"]
                        }))

            # ===== ACCEPT FRIEND =====
            elif t == "accept_friend":
                if not username:
                    continue
                target = data.get("username", "").strip()
                if target not in users[username].get("requests", []):
                    await ws.send(json.dumps({"type": "error", "msg": "No request from this user"}))
                    continue
                users[username]["requests"].remove(target)
                users[username]["friends"].append(target)
                users[target]["friends"].append(username)
                save_data()
                await ws.send(json.dumps({
                    "type": "friend_added", "username": target,
                    "friends": users[username]["friends"],
                    "online_friends": [u for u in online if u != username and u in users[username]["friends"]]
                }))
                if target in online:
                    await online[target].send(json.dumps({"type": "friend_added", "username": username}))

            # ===== TYPING =====
            elif t == "typing":
                if not username: continue
                target = data.get("to")
                if target in online and target in users[username].get("friends",[]):
                    await online[target].send(json.dumps({"type":"typing","from":username}))

            # ===== READ RECEIPT =====
            elif t == "read_receipt":
                if not username: continue
                target = data.get("to")
                if target in online:
                    await online[target].send(json.dumps({"type":"read_receipt","from":username}))

            # ===== DELETE FRIEND =====
            elif t == "delete_friend":
                if not username: continue
                target = data.get("username","").strip()
                if target in users[username].get("friends",[]):
                    users[username]["friends"].remove(target)
                if username in users[target].get("friends",[]):
                    users[target]["friends"].remove(username)
                save_data()
                await ws.send(json.dumps({"type":"friend_deleted","username":target,"friends":users[username]["friends"]}))
                if target in online:
                    await online[target].send(json.dumps({"type":"friend_deleted","username":username,"friends":users[target]["friends"]}))

            # ===== CREATE GROUP =====
            elif t == "create_group":
                if not username: continue
                gname = data.get("name","").strip()
                if not gname:
                    await ws.send(json.dumps({"type":"error","msg":"Group name required"}))
                    continue
                if gname in groups:
                    await ws.send(json.dumps({"type":"error","msg":"Group already exists"}))
                    continue
                groups[gname] = {"name":gname,"creator":username,"members":[username],"history":[]}
                if "groups" not in users[username]:
                    users[username]["groups"] = []
                users[username]["groups"].append(gname)
                save_data()
                print(f"[GROUP] {username} created {gname}")
                await ws.send(json.dumps({"type":"group_created","group":gname,"members":[username]}))

            # ===== ADD TO GROUP =====
            elif t == "add_to_group":
                if not username: continue
                gname = data.get("group","")
                target = data.get("username","").strip()
                if gname not in groups:
                    await ws.send(json.dumps({"type":"error","msg":"Group not found"}))
                    continue
                if username != groups[gname]["creator"]:
                    await ws.send(json.dumps({"type":"error","msg":"Only group creator can add members"}))
                    continue
                if target not in users[username].get("friends",[]):
                    await ws.send(json.dumps({"type":"error","msg":f"{target} is not your friend"}))
                    continue
                if target in groups[gname]["members"]:
                    await ws.send(json.dumps({"type":"error","msg":f"{target} already in group"}))
                    continue
                groups[gname]["members"].append(target)
                if "groups" not in users[target]:
                    users[target]["groups"] = []
                if gname not in users[target]["groups"]:
                    users[target]["groups"].append(gname)
                save_data()

                # Notify all online members
                for m in groups[gname]["members"]:
                    if m in online:
                        await online[m].send(json.dumps({
                            "type":"group_update","group":gname,
                            "members":groups[gname]["members"]
                        }))
                await ws.send(json.dumps({"type":"system","msg":f"{target} added to {gname}"}))

            # ===== GROUP MESSAGE =====
            elif t == "group_msg":
                if not username: continue
                gname = data.get("group","")
                encrypted_b64 = data.get("message","")
                now = data.get("time","")
                if gname not in groups:
                    await ws.send(json.dumps({"type":"error","msg":"Group not found"}))
                    continue
                if username not in groups[gname]["members"]:
                    await ws.send(json.dumps({"type":"error","msg":"You are not in this group"}))
                    continue

                # Decrypt to check type
                try:
                    ed = base64.b64decode(encrypted_b64)
                    pt = decrypt(ed)
                    mt, md, _ = unpack(pt)
                except:
                    mt = None

                if mt == config.MSG_TEXT:
                    text = unpack_text(md)
                    print(f"[GROUP {gname}] {username}: {text}")
                    fp = pack_text(f"[{gname}] {username}: {text}")
                    fb = base64.b64encode(encrypt(fp)).decode()
                    relay = {"type":"group_msg","group":gname,"from":username,"message":fb}
                elif mt == config.MSG_FILE:
                    relay = {"type":"group_file","group":gname,"from":username,"message":encrypted_b64}
                else:
                    relay = {"type":"group_msg","group":gname,"from":username,"message":encrypted_b64}

                # Save to group history
                groups[gname]["history"].append({
                    "from":username,"group":gname,"type":relay["type"],
                    "message":relay.get("message",""),"time":now
                })
                if len(groups[gname]["history"]) > 200:
                    groups[gname]["history"] = groups[gname]["history"][-200:]

                # Relay to all online members except sender
                for m in groups[gname]["members"]:
                    if m != username and m in online:
                        await online[m].send(json.dumps(relay))
                save_data()

            # ===== LEAVE GROUP =====
            elif t == "leave_group":
                if not username: continue
                gname = data.get("group","")
                if gname not in groups:
                    continue
                if username in groups[gname]["members"]:
                    groups[gname]["members"].remove(username)
                if "groups" in users[username] and gname in users[username]["groups"]:
                    users[username]["groups"].remove(gname)
                if len(groups[gname]["members"]) == 0:
                    del groups[gname]
                save_data()
                await ws.send(json.dumps({"type":"group_left","group":gname}))
                print(f"[GROUP] {username} left {gname}")

            # ===== MESSAGE =====
            elif t == "msg":
                encrypted_b64 = data.get("message", "")
                if encrypted_b64:
                    try:
                        ed = base64.b64decode(encrypted_b64)
                        pt = decrypt(ed)
                    except Exception as e:
                        print(f"[SECURITY] Rejected tampered/forged message: {e}")
                        await ws.send(json.dumps({"type": "error", "msg": "HMAC verification failed - message tampered!"}))
                        continue
                if not username:
                    continue
                target = data.get("to")
                now = data.get("time", "")
                print(f"[CIPHER] {encrypted_b64[:60]}...")

                if target not in users[username].get("friends", []):
                    await ws.send(json.dumps({"type": "error", "msg": f"{target} is not your friend"}))
                    continue

                # ---- AI Bot ----
                if target == BOT_NAME and USE_AI:
                    try:
                        ed = base64.b64decode(encrypted_b64)
                        pt = decrypt(ed)
                        mt, md, _ = unpack(pt)
                    except:
                        mt = None

                    if mt == config.MSG_TEXT:
                        user_text = unpack_text(md)
                        print(f"[BOT] {username}: {user_text}")

                        bot_context.setdefault(username, [])
                        bot_context[username].append({"role": "user", "content": user_text})
                        if len(bot_context[username]) > 10:
                            bot_context[username] = bot_context[username][-10:]

                        bot_reply = "(aiohttp not installed)"
                        try:
                            import aiohttp
                            async with aiohttp.ClientSession() as session:
                                async with session.post(
                                    f"{AI_BASE_URL}/chat/completions",
                                    headers={
                                        "Authorization": f"Bearer {AI_API_KEY}",
                                        "Content-Type": "application/json"
                                    },
                                    json={
                                        "model": AI_MODEL,
                                        "messages": [
                                            {"role": "system", "content": "Reply in the same language as the user. Keep replies concise."}
                                        ] + bot_context[username]
                                    },
                                    timeout=aiohttp.ClientTimeout(total=30)
                                ) as resp:
                                    if resp.status == 200:
                                        result = await resp.json()
                                        bot_reply = result["choices"][0]["message"]["content"]
                                    else:
                                        bot_reply = f"(API error {resp.status})"
                        except ImportError:
                            bot_reply = "(aiohttp not installed. Run: pip install aiohttp)"
                        except Exception as e:
                            bot_reply = f"(Bot error: {e})"

                        bot_context[username].append({"role": "assistant", "content": bot_reply})
                        print(f"[BOT] reply: {bot_reply}")

                        fp = pack_text(f"{BOT_NAME}: {bot_reply}")
                        fe = encrypt(fp)
                        fb = base64.b64encode(fe).decode()
                        await ws.send(json.dumps({"type": "msg", "from": BOT_NAME, "message": fb}))

                        history.setdefault(username, []).append(
                            {"from": username, "to": BOT_NAME, "type": "msg", "message": encrypted_b64, "time": now})
                        history.setdefault(username, []).append(
                            {"from": BOT_NAME, "to": username, "type": "msg", "message": fb, "time": now})
                        save_data()
                    continue
                # ---- End AI Bot ----

                # Normal message relay
                # Detect message type first
                try:
                    ed = base64.b64decode(encrypted_b64)
                    pt = decrypt(ed)
                    mt, md, _ = unpack(pt)
                except ValueError as e:
                    if "HMAC" in str(e):
                        print(f"[SECURITY] HMAC verification failed from {username}!")
                        await ws.send(json.dumps({"type": "error", "msg": "HMAC verification failed - message may be tampered!"}))
                        continue
                    mt = None
                except:
                    mt = None

                msg_type = "file" if mt == config.MSG_FILE else "msg"
                entry_s = {"from": username, "to": target, "type": msg_type,
                           "message": encrypted_b64, "time": now}
                history.setdefault(username, []).append(entry_s)

                if target in online:
                    if mt == config.MSG_TEXT:
                        text = unpack_text(md)
                        print(f"[{username} -> {target}] {text}")
                        fp = pack_text(f"{username}: {text}")
                        fb = base64.b64encode(encrypt(fp)).decode()
                        relay = {"type": "msg", "from": username, "message": fb}
                    elif mt == config.MSG_FILE:
                        relay = {"type": "file", "from": username, "message": encrypted_b64}
                    else:
                        relay = {"type": "msg", "from": username, "message": encrypted_b64}

                    await online[target].send(json.dumps(relay))
                    history.setdefault(target, []).append({
                        "from": username, "to": target,
                        "type": relay["type"], "message": relay.get("message", ""), "time": now
                    })
                else:
                    history.setdefault(target, []).append({
                        "from": username, "to": target,
                        "type": msg_type, "message": encrypted_b64, "time": now
                    })
                    await ws.send(json.dumps({
                        "type": "system", "msg": f"Message queued: {target} is offline"
                    }))

    except Exception as e:
        print(f"[!] {username} error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if username and username in online:
            del online[username]
            print(f"[-] {username} offline")
            await broadcast_system(f"{username} left")

# ---- Main ----
async def main():
    load_data()
    ensure_bot()
    save_data()
    print(f"WebSocket server: ws://{config.HOST}:{config.WS_PORT}")
    async with serve(handler, config.HOST, config.WS_PORT, max_size=50_000_000):
        await asyncio.get_running_loop().create_future()

if __name__ == "__main__":
    asyncio.run(main())
