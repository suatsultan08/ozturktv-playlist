import urllib.request
import ssl
import concurrent.futures

# SSL hatalarını yok sayan güvenli bağlam
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

SOURCE_URLS = [
    "https://gist.githubusercontent.com/suatsultan08/002cbfc4fd3524cac8fae3e041641ff9/raw/kanallar.txt",
    "https://iptv-org.github.io/iptv/countries/tr.m3u"
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

def parse_playlist_recursive(source_url, visited=None):
    """Hem kanallar.txt'yi hem de içindeki alt .m3u linklerini içeri dalıp çözer"""
    if visited is None:
        visited = set()
    
    if source_url in visited:
        return []
    visited.add(source_url)

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

                # Standart #EXTINF satırı
                if line.startswith("#EXTINF"):
                    current_extinf = line

                # URL satırı yakalandı
                elif line.startswith("http://") or line.startswith("https://"):
                    # Eğer bu bir alt M3U listesiyse içine girip kanallarını çek
                    if ".m3u" in line.lower() or "playlist" in line.lower() or ".txt" in line.lower():
                        print(f"🔗 Alt liste bulundu, içeriğe dalınıyor: {line}")
                        items.extend(parse_playlist_recursive(line, visited))
                        current_extinf = ""
                    elif current_extinf:
                        items.append((current_extinf, line))
                        current_extinf = ""

                # 'Kanal Adı | URL' veya 'Liste Adı | M3U_URL' formatı
                elif "|" in line:
                    parts = line.split("|")
                    title = parts[0].strip()
                    url = parts[1].strip()
                    if url.startswith("http"):
                        if ".m3u" in url.lower() or "playlist" in url.lower() or ".txt" in url.lower():
                            print(f"🔗 Alt liste linki bulundu: {title} -> {url}")
                            items.extend(parse_playlist_recursive(url, visited))
                        else:
                            items.append((f'#EXTINF:-1 group-title="Genel",{title}', url))
    except Exception as e:
        print(f"Uyarı: {source_url} ayrıştırılamadı -> {e}")
    return items

def main():
    print("Kanal listeleri ve alt M3U kaynakları taranıyor...")
    raw_list = []

    for s in SOURCE_URLS:
        raw_list.extend(parse_playlist_recursive(s))

    # Tekrarlanan yayın linklerini temizle
    unique_channels = {}
    for extinf, url in raw_list:
        if url not in unique_channels:
            unique_channels[url] = extinf

    total_test = [(extinf, url) for url, extinf in unique_channels.items()]
    print(f"Toplam test edilecek canlı yayın sayısı: {len(total_test)}")

    working_list = []
    if total_test:
        with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
            results = executor.map(is_link_alive, total_test)
            for name, url, alive in results:
                ch_title = name.split(',')[-1]
                if alive:
                    working_list.append((name, url))
                    print(f"✅ ÇALIŞIYOR: {ch_title}")
                else:
                    print(f"❌ KOPUK: {ch_title}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for name, url in working_list:
            f.write(f"{name}\n{url}\n")

    print(f"Tamamlandı! Toplam {len(working_list)} çalışan kanal '{OUTPUT_FILE}' dosyasına yazıldı.")

if __name__ == "__main__":
    main()
