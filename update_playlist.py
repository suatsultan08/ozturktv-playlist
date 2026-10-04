
import urllib.request
import concurrent.futures

# Taranacak ham kaynaklar (Buraya istediğin kadar ham M3U veya TXT koyabilirsin)
SOURCE_URLS = [
    "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlists/playlist_turkey.m3u8",
    "https://iptv-org.github.io/iptv/countries/tr.m3u"
]

OUTPUT_FILE = "canli_kanallar.m3u"

def is_link_alive(url):
    """Linkin anında canlı yayın verip vermediğini test eder"""
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
        )
        # 3 saniye içinde ilk paket gelmezse o kanalı ölü/donuyor kabul eder
        with urllib.request.urlopen(req, timeout=3.5) as response:
            return response.status in [200, 301, 302]
    except Exception:
        return False

def main():
    print("Kanallar taranıyor...")
    channels = []
    
    # Kaynak listeleri oku
    for s_url in SOURCE_URLS:
        try:
            req = urllib.request.Request(s_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                lines = resp.read().decode('utf-8', errors='ignore').splitlines()
                
                name = ""
                for line in lines:
                    line = line.strip()
                    if line.startswith("#EXTINF"):
                        name = line
                    elif (line.startswith("http://") or line.startswith("https://")) and name:
                        channels.append((name, line))
                        name = ""
        except Exception as e:
            print(f"Hata: {s_url} çekilemedi: {e}")

    # Tekrarlanan kanalları temizle
    unique_channels = {}
    for name, stream_url in channels:
        if stream_url not in unique_channels:
            unique_channels[stream_url] = name

    print(f"Toplam {len(unique_channels)} link test ediliyor...")

    # Hepsini aynı anda hızlıca test et (Multi-thread)
    working_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        future_to_channel = {executor.submit(is_link_alive, url): (name, url) for url, name in unique_channels.items()}
        for future in concurrent.futures.as_completed(future_to_channel):
            name, url = future_to_channel[future]
            try:
                if future.result():
                    working_list.append((name, url))
                    print(f"✅ ÇALIŞIYOR: {name.split(',')[-1]}")
                else:
                    print(f"❌ ÖLÜ: {name.split(',')[-1]}")
            except Exception:
                pass

    # Sadece çalışan tertemiz listeyi M3U olarak kaydet
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for name, url in working_list:
            f.write(f"{name}\n{url}\n")

    print(f"\nİşlem bitti! Toplam {len(working_list)} çalışan kanal '{OUTPUT_FILE}' dosyasına kaydedildi.")

if __name__ == "__main__":
    main()
