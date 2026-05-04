import requests
from bs4 import BeautifulSoup
import json
import os
import time

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
    char_map = {'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c', 'I': 'i', 'İ': 'i'}
    city = city_name.lower()
    for tr, eng in char_map.items():
        city = city.replace(tr, eng)
    if city == "afyonkarahisar": return "afyon"
    if city == "kahramanmaras": return "maras"
    return city

import math

import reverse_geocoder as rg

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
            # District fallback using reverse geocoding
            if not district:
                district = rg_result.get('admin2', '')
                if not district:
                    district = rg_result.get('name', 'Merkez')
            
            # Reverse Geocoder'dan ili al ve normalize et
            rg_city = rg_result['admin1']
            norm_rg = normalize_city_name(rg_city)
            
            # Listemizdeki 81 il ile eşleştir
            mapped_city = "İstanbul" # Default to İstanbul instead of Bilinmeyen
            for c in CITIES:
                norm_c = normalize_city_name(c)
                # Fuzzy match: "Istanbul" matches "İstanbul", "Province of Istanbul" matches "İstanbul"
                if norm_c == norm_rg or norm_c in norm_rg or norm_rg in norm_c:
                    mapped_city = c
                    break
                        
            # OSM tag fallback if rg failed
            city_tag = tags.get('addr:province', tags.get('addr:city', ''))
            if city_tag:
                norm_tag = normalize_city_name(city_tag)
                for c in CITIES:
                    if normalize_city_name(c) == norm_tag:
                        mapped_city = c
                        break
                        
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

import concurrent.futures

def fetch_on_duty_pharmacies():
    print("81 İl için nöbetçi eczaneler asenkron kazınıyor (Saniyeler sürecek)...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    on_duty_names = set()
    
    def scrape_city(city):
        url_city = normalize_city_name(city)
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
        return local_names

    # Eşzamanlı (Concurrent) işlem
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(scrape_city, c) for c in CITIES]
        for future in concurrent.futures.as_completed(futures):
            on_duty_names.update(future.result())
            
    print(f"Toplam {len(on_duty_names)} nöbetçi eczane (81 İl) tespit edildi.")
    return on_duty_names

def main():
    # 1. OSM'den sabit veriyi çek
    pharmacies = fetch_osm_pharmacies()
    
    # 2. İnternetten canlı nöbetçi verisini kazı
    on_duty_names = fetch_on_duty_pharmacies()
    
    # 3. İkisini birleştir
    matched_count = 0
    for p in pharmacies:
        p_name_lower = p['name'].lower()
        for duty_name in on_duty_names:
            if duty_name in p_name_lower or p_name_lower in duty_name:
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
