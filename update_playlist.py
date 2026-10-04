import urllib.request
import ssl
import concurrent.futures

# SSL ve Sertifika hatalarını yok sayan güvenli bağlam
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Bizim kaynaklarımız
SOURCE_URLS = [
    "https://gist.githubusercontent.com/suatsultan08/002cbfc4fd3524cac8fae3e041641ff9/raw/kanallar.txt",
    
]

OUTPUT_FILE = "canli_kanallar.m3u"

def is_link_alive(channel_data):
    name, url = channel_data
    try:
        req = urllib.request.Request(
            url, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            }
        )
        with urllib.request.urlopen(req, timeout=3.5, context=ctx) as response:
            if response.status in [200, 301, 302]:
                return (name, url, True)
    except Exception:
        pass
    return (name, url, False)

def fetch_content(source_url):
    items = []
    try:
        req = urllib.request.Request(
            source_url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            lines = content.splitlines()

            current_extinf = ""
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#EXTM3U"):
                    continue

                if line.startswith("#EXTINF"):
                    current_extinf = line
                elif (line.startswith("http://") or line.startswith("https://")) and current_extinf:
                    items.append((current_extinf, line))
                    current_extinf = ""
                elif "|" in line:
                    parts = line.split("|")
                    ch_name = parts[0].strip()
                    ch_url = parts[1].strip()
                    if ch_url.startswith("http"):
                        items.append((f'#EXTINF:-1 group-title="Genel",{ch_name}', ch_url))
    except Exception as e:
        print(f"Uyarı: {source_url} çekilirken atlandı -> {e}")
    return items

def main():
    print("Kaynaklar taranıyor...")
    raw_list = []

    for s in SOURCE_URLS:
        raw_list.extend(fetch_content(s))

    # Tekilleştirme
    unique_channels = {}
    for extinf, url in raw_list:
        if url not in unique_channels:
            unique_channels[url] = extinf

    total_test = [(extinf, url) for url, extinf in unique_channels.items()]
    print(f"Toplam test edilecek kanal sayısı: {len(total_test)}")

    working_list = []
    if total_test:
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            results = executor.map(is_link_alive, total_test)
            for name, url, alive in results:
                ch_title = name.split(',')[-1]
                if alive:
                    working_list.append((name, url))
                    print(f"✅ ÇALIŞIYOR: {ch_title}")
                else:
                    print(f"❌ KOPUK: {ch_title}")

    # Dosyayı her halükarda oluştur
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for name, url in working_list:
            f.write(f"{name}\n{url}\n")

    print(f"Tamamlandı! {len(working_list)} çalışan kanal '{OUTPUT_FILE}' dosyasına yazıldı.")

if __name__ == "__main__":
    main()
