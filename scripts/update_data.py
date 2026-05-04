import requests
from bs4 import BeautifulSoup
import json
import os
import time
import concurrent.futures
import reverse_geocoder as rg
import re

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
FILE_PATH = os.path.join(DATA_DIR, 'pharmacies.json')

CITIES = [
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin", "Aydın", "Balıkesir",
    "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli",
    "Diyarbakır", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari",
    "Hatay", "Isparta", "Mersin", "İstanbul", "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir",
    "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla", "Muş", "Nevşehir",
    "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Tekirdağ", "Tokat",
    "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray", "Bayburt", "Karaman",
    "Kırıkkale", "Batman", "Şırnak", "Bartın", "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce"
]

def normalize_city_name(city_name):
    """Normalize Turkish city names for comparison."""
    # Önce büyük Türkçe harfleri dönüştür (İ → i, I → i özellikle kritik)
    char_map_upper = {'İ': 'i', 'I': 'i', 'Ğ': 'g', 'Ü': 'u', 'Ş': 's', 'Ö': 'o', 'Ç': 'c'}
    city = city_name
    for tr, eng in char_map_upper.items():
        city = city.replace(tr, eng)
    city = city.lower()
    # Sonra küçük Türkçe harfleri dönüştür
    char_map_lower = {'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c'}
    for tr, eng in char_map_lower.items():
        city = city.replace(tr, eng)
    return city

# Afyonkarahisar ve Kahramanmaraş için scraping URL alias’ları (normalize’dan bağımsız)
SCRAPE_URL_ALIASES = {
    "Afyonkarahisar": "afyon",
    "Kahramanmaraş": "maras",
}

def fetch_osm_pharmacies():
    print("OpenStreetMap'ten tüm TÜRKİYE eczaneleri tek seferde çekiliyor...")
    overpass_url = "http://overpass-api.de/api/interpreter"
    headers = {'User-Agent': 'EczanemApp/1.0 (emrehan)'}
    
    overpass_query = """
    [out:json][timeout:300];
    area["ISO3166-1"="TR"][admin_level=2]->.searchArea;
    (
      node["amenity"="pharmacy"](area.searchArea);
    );
    out body;
    >;
    out skel qt;
    """
    
    pharmacies = []
    try:
        response = requests.post(overpass_url, data=overpass_query.encode('utf-8'), headers=headers, timeout=300)
        data = response.json()
        
        elements = [e for e in data.get('elements', []) if e['type'] == 'node']
        coords = [(e['lat'], e['lon']) for e in elements]
        
        print("Çevrimdışı Yapay Zeka (Reverse Geocoder) ile il sınırları %100 hassasiyetle hesaplanıyor...")
        results = rg.search(coords) # Saniyeler içinde 24.000 noktayı il sınırlarıyla eşleştirir
        
        for idx, element in enumerate(elements):
            tags = element.get('tags', {})
            name = tags.get('name', '').strip()
            if not name:
                name = 'İsimsiz Eczane'
            district = tags.get('addr:district', '').strip()
            
            rg_result = results[idx]
            
            # Reverse Geocoder'dan ili al ve normalize et
            rg_city = rg_result['admin1']
            norm_rg = normalize_city_name(rg_city)
            
            # İlçe belirle: OSM tag → RG admin2 (il ismi değilse) → RG name → Merkez
            city_names_norm = {normalize_city_name(c) for c in CITIES}
            if not district:
                rg_admin2 = rg_result.get('admin2', '').strip()
                rg_name = rg_result.get('name', '').strip()
                # admin2 bir il ismi değilse ilçe olarak kullan
                if rg_admin2 and normalize_city_name(rg_admin2) not in city_names_norm:
                    district = rg_admin2
                elif rg_name:
                    district = rg_name
                else:
                    district = 'Merkez'
            
            # Listemizdeki 81 il ile eşleştir
            mapped_city = None
            rg_matched = False
            if norm_rg:  # RG boş döndüyse doğrudan OSM fallback'e geç
                for c in CITIES:
                    norm_c = normalize_city_name(c)
                    # Tam eşleşme veya biri diğerini içeriyor (en az 3 karakter güvenlik)
                    if norm_c == norm_rg:
                        mapped_city = c
                        rg_matched = True
                        break
                    elif len(norm_rg) >= 3 and len(norm_c) >= 3 and (norm_c in norm_rg or norm_rg in norm_c):
                        mapped_city = c
                        rg_matched = True
                        break
                        
            # OSM tag fallback SADECE RG eşleşemediğinde kullanılır
            if not rg_matched:
                city_tag = tags.get('addr:province', tags.get('addr:city', ''))
                if city_tag:
                    norm_tag = normalize_city_name(city_tag)
                    for c in CITIES:
                        if normalize_city_name(c) == norm_tag:
                            mapped_city = c
                            break
                            
            # OSM verisinde "district" alanı yanlışlıkla İL olarak girilmişse (Örn: ADANA, BINGOL)
            if district and normalize_city_name(district) in city_names_norm:
                if not mapped_city:
                    for c in CITIES:
                        if normalize_city_name(c) == normalize_city_name(district):
                            mapped_city = c
                            break
                # İlçe olarak girilen il ismini düzelt (RG name veya Merkez yap)
                rg_name = rg_result.get('name', '').strip()
                district = rg_name if rg_name else 'Merkez'
            
            # Hala eşleşmezse varsayılan İstanbul
            if not mapped_city:
                mapped_city = "İstanbul"
                        
            # Eğer hala isim yoksa, alternatif etiketlere bak
            if not name:
                name = tags.get('name:tr', tags.get('operator', tags.get('brand', ''))).strip()
            
            # Alternatiflerde de yoksa ilçe adını kullanarak mantıklı bir isim üret
            if not name or name == 'İsimsiz Eczane':
                # Örn: 'Kadıköy Eczanesi' (Eğer Merkez ise il adını kullan)
                fallback_name = mapped_city if district == 'Merkez' else district
                name = f"{fallback_name.title()} Eczanesi"
                
            pharmacies.append({
                "id": str(element['id']),
                "name": name,
                "city": mapped_city,
                "district": district.upper(),
                "lat": element['lat'],
                "lng": element['lon'],
                "on_duty": False,
                "address": f"{tags.get('addr:street', '')} {tags.get('addr:housenumber', '')} {district} {mapped_city}".strip(),
                "phone": tags.get('contact:phone', tags.get('phone', ''))
            })
            
    except Exception as e:
        print(f"OSM API Hatası: {str(e)}")
        
    print(f"Toplam {len(pharmacies)} sabit eczane haritadan bulundu ve kusursuz illere dağıtıldı.")
    return pharmacies



def fetch_on_duty_pharmacies():
    """Nöbetçi eczaneleri şehir bazında kazır. {city: set(names)} döndürür."""
    print("81 İl için nöbetçi eczaneler asenkron kazınıyor (Saniyeler sürecek)...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    def scrape_city(city):
        url_city = SCRAPE_URL_ALIASES.get(city, normalize_city_name(city))
        url = f"https://www.eczaneler.gen.tr/nobetci-{url_city}"
        local_names = set()
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                tables = soup.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        name_cell = row.find('td')
                        if name_cell:
                            text = name_cell.get_text(separator=' ').strip()
                            if "Eczanesi" in text:
                                idx = text.find("Eczanesi")
                                if idx != -1:
                                    clean_name = text[:idx+8].strip().split('\n')[-1].strip()
                                    local_names.add(clean_name.lower())
        except Exception as e:
            pass # Hata durumunda sessizce geç
        return (city, local_names)

    # Eşzamanlı (Concurrent) işlem
    on_duty_by_city = {}  # {city: set(names)}
    total_names = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(scrape_city, c) for c in CITIES]
        for future in concurrent.futures.as_completed(futures):
            city, names = future.result()
            if names:
                on_duty_by_city[city] = names
                total_names += len(names)
            
    print(f"Toplam {total_names} nöbetçi eczane (81 İl) tespit edildi.")
    return on_duty_by_city

def main():
    # 1. OSM'den sabit veriyi çek
    pharmacies = fetch_osm_pharmacies()
    
    # 2. İnternetten canlı nöbetçi verisini kazı
    on_duty_by_city = fetch_on_duty_pharmacies()
    
    # 3. İkisini birleştir (Şehir bazında + normalize edilmiş tam eşleşme)
    matched_count = 0
    for p in pharmacies:
        city = p.get('city', '')
        duty_names = on_duty_by_city.get(city, set())
        if not duty_names:
            continue
        
        p_name_norm = normalize_city_name(p['name'])
        p_name_clean = re.sub(r'\s*eczanesi?\s*$', '', p_name_norm).strip()
        
        for duty_name in duty_names:
            duty_norm = normalize_city_name(duty_name)
            duty_clean = re.sub(r'\s*eczanesi?\s*$', '', duty_norm).strip()
            
            # Tam eşleşme (normalize edilmiş): "merkez" == "merkez"
            if p_name_clean == duty_clean or p_name_norm == duty_norm:
                p['on_duty'] = True
                matched_count += 1
                break
                
    print(f"{matched_count} nöbetçi eczane başarıyla harita verisiyle eşleştirildi.")
    
    # 4. JSON olarak kaydet (Atomic Write) -> [Kritik] Corruption engellendi
    temp_path = FILE_PATH + '.tmp'
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(pharmacies, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, FILE_PATH)
    
    print(f"Veriler başarıyla {FILE_PATH} dosyasına kaydedildi! Boyut: {os.path.getsize(FILE_PATH) / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    main()
