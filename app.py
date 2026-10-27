import os, threading, time, json
from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

STATE = {
    "running": False,
    "name": "",
    "last_name": "",
    "api_token": "",
    "page_id": "",
    "interval": 60,
    "mode": "post",          # post | messenger
    "posts": [],
    "contacts": [],
    "log": [],
    "counter": 0,
    "owner": "OWNER MR SURAJ 🩵"
}

def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    STATE["log"].append(line)
    STATE["log"] = STATE["log"][-200:]   # last 200 lines
    print(line, flush=True)

def post_to_page(msg):
    url = f"https://graph.facebook.com/v21.0/{STATE['page_id']}/feed"
    r = requests.post(url, data={"message": msg,
                                 "access_token": STATE["api_token"]}, timeout=30)
    return r.json()

def send_messenger(psid, text):
    url = f"https://graph.facebook.com/v21.0/{STATE['page_id']}/messages"
    payload = {
        "recipient": {"id": psid},
        "message": {"text": text},
        "access_token": STATE["api_token"]
    }
    r = requests.post(url, json=payload, timeout=30)
    return r.json()

def worker_loop():
    idx = 0
    while STATE["running"]:
        try:
            if STATE["mode"] == "post" and STATE["posts"]:
                msg = STATE["posts"][idx % len(STATE["posts"])]
                res = post_to_page(msg)
                if "id" in res:
                    log(f"✅ Post OK → {res['id']}")
                else:
                    log(f"❌ Post FAIL → {res}")
            elif STATE["mode"] == "messenger" and STATE["contacts"]:
                psid = STATE["contacts"][idx % len(STATE["contacts"])]
                res = send_messenger(psid, STATE["posts"][0] if STATE["posts"] else "Hello!")
                if "message_id" in res:
                    log(f"✅ Msg OK → {psid}")
                else:
                    log(f"❌ Msg FAIL → {res}")
            idx += 1
            STATE["counter"] += 1
            for _ in range(STATE["interval"]):
                if not STATE["running"]:
                    break
                time.sleep(1)
        except Exception as e:
            log(f"⚠️ Error: {e}")
            time.sleep(10)

@app.route("/")
def home():
    return render_template("index.html", owner=STATE["owner"])

@app.route("/start", methods=["POST"])
def start():
    d = request.json
    STATE.update({
        "name": d.get("name", ""),
        "last_name": d.get("last_name", ""),
        "api_token": d.get("api_token", ""),
        "page_id": d.get("page_id", ""),
        "interval": int(d.get("interval", 60)),
        "mode": d.get("mode", "post"),
        "counter": 0
    })
    # Load files from data/
    if os.path.exists("data/posts.txt"):
        STATE["posts"] = [l.strip() for l in open("data/posts.txt", encoding="utf-8") if l.strip()]
    if os.path.exists("data/contacts.csv"):
        STATE["contacts"] = [l.strip().split(",")[0] for l in open("data/contacts.csv", encoding="utf-8") if l.strip()]

    if not STATE["running"]:
        STATE["running"] = True
        threading.Thread(target=worker_loop, daemon=True).start()
        log(f"🚀 Started by {STATE['name']} {STATE['last_name']} | Mode={STATE['mode']}")
    return jsonify({"ok": True})

@app.route("/stop", methods=["POST"])
def stop():
    STATE["running"] = False
    log("🛑 Stopped")
    return jsonify({"ok": True})

@app.route("/status")
def status():
    return jsonify({
        "running": STATE["running"],
        "counter": STATE["counter"],
        "log": STATE["log"][-50:],
        "owner": STATE["owner"]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
