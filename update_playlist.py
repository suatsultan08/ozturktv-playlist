import urllib.request
import concurrent.futures

# TAM OLARAK BİZİM PROJEDE KULLANDIĞIN KENDİ LİSTELERİN:
SOURCE_URLS = [
    # 1. Senin GitHub Gist'teki asıl liste dosyan
    "https://gist.githubusercontent.com/suatsultan08/002cbfc4fd3524cac8fae3e041641ff9/raw/kanallar.txt",
    # 2. Projede varsayılan kullandığımız Türk kanalları listesi
    "https://iptv-org.github.io/iptv/countries/tr.m3u"
]

OUTPUT_FILE = "canli_kanallar.m3u"

def is_link_alive(channel_data):
    name, url = channel_data
    try:
        # IPTV sunucularının engellememesi için tarayıcı kimliği
        req = urllib.request.Request(
            url, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            }
        )
        # 3.5 saniye içinde cevap vermeyen veya donan linki doğrudan eler
        with urllib.request.urlopen(req, timeout=3.5) as response:
            if response.status in [200, 301, 302]:
                return (name, url, True)
    except Exception:
        pass
    return (name, url, False)

def fetch_m3u_or_txt(source_url):
    """Hem standart M3U linklerini hem de senin kanallar.txt formatını (Kanal|URL) okur"""
    items = []
    try:
        req = urllib.request.Request(source_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            lines = content.splitlines()

            current_extinf = ""
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#EXTM3U"):
                    continue

                # Eğer M3U formatıysa (#EXTINF:...)
                if line.startswith("#EXTINF"):
                    current_extinf = line
                elif (line.startswith("http://") or line.startswith("https://")) and current_extinf:
                    items.append((current_extinf, line))
                    current_extinf = ""

                # Eğer senin kanallar.txt gibi 'Kanal Adı | URL' formatıysa
                elif "|" in line:
                    parts = line.split("|")
                    ch_name = parts[0].strip()
                    ch_url = parts[1].strip()
                    if ch_url.startswith("http"):
                        extinf_line = f'#EXTINF:-1 group-title="Genel",{ch_name}'
                        items.append((extinf_line, ch_url))

                # Eğer satırda sadece M3U linki varsa (alt liste linki)
                elif line.startswith("http://") or line.startswith("https://"):
                    # Bu link bir alt M3U listesi olabilir, onu da içeri çek
                    if ".m3u" in line.lower() or "playlist" in line.lower():
                        items.extend(fetch_m3u_or_txt(line))
    except Exception as e:
        print(f"Hata: {source_url} okunamadı -> {e}")
    return items

def main():
    print("Bizim projenin kanal kaynakları taranıyor...")
    all_raw_channels = []

    for s_url in SOURCE_URLS:
        all_raw_channels.extend(fetch_m3u_or_txt(s_url))

    # Tekrarlanan URL'leri ayıkla
    unique_channels = {}
    for extinf, url in all_raw_channels:
        if url not in unique_channels:
            unique_channels[url] = extinf

    total_list = [(extinf, url) for url, extinf in unique_channels.items()]
    print(f"Toplam {len(total_list)} adet bizim kanal linki test ediliyor...")

    working_list = []
    # 25 paralel bağlantı ile hızla test et
    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
        results = executor.map(is_link_alive, total_list)
        for name, url, alive in results:
            ch_title = name.split(',')[-1]
            if alive:
                working_list.append((name, url))
                print(f"✅ ÇALIŞIYOR (Eklendi): {ch_title}")
            else:
                print(f"❌ KOPUK / ÖLÜ (Elendi): {ch_title}")

    print(f"\nİşlem Bitti! {len(total_list)} link arasından {len(working_list)} çalışan kanal seçildi.")

    # Sadece çalışanları tertemiz M3U olarak kaydet
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for name, url in working_list:
            f.write(f"{name}\n{url}\n")

    print(f"'{OUTPUT_FILE}' dosyası oluşturuldu.")

if __name__ == "__main__":
    main()
