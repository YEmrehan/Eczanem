# 🔍 Eczanem — Mantık Hatası Denetim Raporu

---

## 🔴 KRİTİK

### 1. Stok Verileri Sahte ve Her Restart'ta Değişiyor
**Dosya:** [index.py:54-66](file:///media/emrehan/HDD/github/Eczanem/api/index.py#L54-L66)

`PRODUCTS` listesi sunucu her başlatıldığında (`uvicorn --reload`) `random.randint()` ile yeniden üretiliyor. Bu demek oluyor ki:
- Admin panelinde gördüğün stok sayıları **her sayfa yenilemede farklı** (sunucu reload olduğunda)
- Ürünler sayfasındaki stoklar **gerçek veri değil**, tamamen rastgele
- Bir eczanenin gerçekte hangi ürünleri sattığıyla hiçbir ilgisi yok

```python
# Her restart'ta farklı sonuç veren kod:
stock_count = 0 if random.random() < 0.2 else random.randint(1, 50)
```

**Etki:** Kullanıcı "Bu eczanede Parol var mı?" diye bakarsa, gördüğü bilgi tamamen uydurma.

---

### 2. Nöbetçi Eşleştirme Algoritması Çok Fazla Yanlış Pozitif Veriyor
**Dosya:** [update_data.py:164-172](file:///media/emrehan/HDD/github/Eczanem/scripts/update_data.py#L164-L172)

Nöbetçi eczane eşleştirme mantığı **alt-metin (substring) karşılaştırması** yapıyor:

```python
if duty_name in p_name_lower or p_name_lower in duty_name:
    p['on_duty'] = True
```

Bu mantıkla:
- `"merkez eczanesi"` nöbetçiyse, adında `"merkez"` geçen **TÜM eczaneler** nöbetçi olarak işaretleniyor
- `"sağlık eczanesi"` nöbetçiyse, `"halk sağlık eczanesi"` de nöbetçi oluyor
- **Sonuç:** 1.805 gerçek nöbetçi yerine **16.076 eczane** nöbetçi olarak eşleştirilmiş (logda görünüyor!)

> [!CAUTION]
> 24.054 eczaneden 16.076'sı nöbetçi olarak işaretlenmiş. Gerçekte bu oran yaklaşık %3-5 olmalı ama şu an **%67**. Bu tamamen yanlış.

---

### 3. OSM Fallback Her Zaman RG Sonucunu Eziyor
**Dosya:** [update_data.py:88-95](file:///media/emrehan/HDD/github/Eczanem/scripts/update_data.py#L88-L95)

OSM tag fallback kodu `mapped_city == "Bilinmeyen İl"` kontrolü olmadan çalışıyor. Reverse Geocoder doğru şehri bulsa bile, eğer OSM etiketinde farklı bir şehir yazıyorsa **onu ezip yazıyor:**

```python
# Bu blok HER ZAMAN çalışıyor, mapped_city doğru olsa bile:
city_tag = tags.get('addr:province', tags.get('addr:city', ''))
if city_tag:
    norm_tag = normalize_city_name(city_tag)
    for c in CITIES:
        if normalize_city_name(c) == norm_tag:
            mapped_city = c  # Doğru olan RG sonucunu eziyor!
            break
```

**Etki:** RG ile doğru bulunan şehir, hatalı OSM etiketi yüzünden yanlış şehre kaydırılabiliyor.

---

## 🟠 ÖNEMLİ

### 4. `/api/pharmacies` Tüm 24.000 Eczaneyi Filtresiz Döndürüyor
**Dosya:** [index.py:196-198](file:///media/emrehan/HDD/github/Eczanem/api/index.py#L196-L198)

```python
@app.get("/api/pharmacies")
async def api_pharmacies():
    return PHARMACIES  # 24.000 kayıt, ~5.7 MB JSON
```

Ana sayfa her yüklendiğinde tarayıcı **5.7 MB JSON** indiriyor. Mobilde bu:
- Yavaş ağlarda 5-10 saniye bekleme
- Tarayıcının 24.000 nesneyi parse etmesi gerekiyor
- Tüm bu veri bellekte tutuluyor

---

### 5. Şehir Eşleştirmesinde Yanlış Pozitif Riski (`norm_rg in norm_c`)
**Dosya:** [update_data.py:84](file:///media/emrehan/HDD/github/Eczanem/scripts/update_data.py#L84)

```python
if norm_c == norm_rg or norm_c in norm_rg or norm_rg in norm_c:
```

`norm_rg in norm_c` kontrolü tehlikeli. Örneğin:
- RG `"van"` döndürürse → `"diyarbakır"` ile eşleşmez ama `"yalova"` ile de eşleşmez (güvenli)
- **Ancak** RG kısa bir değer döndürürse (`"is"` gibi), `"istanbul"` ile eşleşir
- `"art"` → `"artvin"` ile eşleşir ama `"kars"` → `"kahramanmaras"` ile de eşleşir!

---

### 6. Ürünler Sayfasında `city` Forumda Gizli Alan Olarak Korunmuyor
**Dosya:** [products.html:55-57](file:///media/emrehan/HDD/github/Eczanem/templates/products.html#L55-L57)

Formda sadece `category` için hidden input var ama `city` yok:

```html
{% if active_category %}
<input type="hidden" name="category" value="{{ active_category }}">
{% endif %}
<!-- city için hidden input yok! -->
```

Kullanıcı "Filtrele" butonuna basarsa, form submit'te `city` seçimi korunuyor (select element'ten). **Ancak** arama kutusuna yazıp Enter'a basarsa, city formdaki select'ten alınır — bu güvenli. Asıl sorun: city select'te `onchange` ile `this.form.pharmacy.value=''` yapılıyor ama category sıfırlanmıyor. Yani şehir değiştirince eski kategori filtresini tutuyor.

---

## 🟡 ORTA

### 7. `normalize_city_name()` Fonksiyonundaki Afyon/Maraş Kısaltması Tek Yönlü
**Dosya:** [update_data.py:26-27](file:///media/emrehan/HDD/github/Eczanem/scripts/update_data.py#L26-L27)

```python
if city == "afyonkarahisar": return "afyon"
if city == "kahramanmaras": return "maras"
```

Bu kısaltma, `normalize_city_name("Afyonkarahisar")` → `"afyon"` döndürüyor. Ama Reverse Geocoder `"Afyon"` döndürürse → `"afyon"` olur ve `CITIES` listesindeki `"Afyonkarahisar"` → `normalize` → `"afyon"` ile eşleşir. **BU kısım doğru çalışıyor.**

Ancak nöbetçi scraping URL'sinde sorun var:
```python
url = f"https://www.eczaneler.gen.tr/nobetci-{url_city}"
# Afyonkarahisar → "nobetci-afyon" (doğru mu? site "nobetci-afyonkarahisar" bekliyor olabilir)
```

---

### 8. Admin Panelinde Sayfa Kontrolü Yok — Negatif veya Aşırı Büyük Sayfa Numarası
**Dosya:** [index.py:168-169](file:///media/emrehan/HDD/github/Eczanem/api/index.py#L168-L169)

```python
page: int = Query(default=1),
limit: int = Query(default=50)
```

`/admin?page=-5` veya `/admin?page=999999` gibi isteklerde:
- Negatif sayfa → boş tablo
- Aşırı büyük sayfa → boş tablo, hata mesajı yok
- `limit=0` → sonsuz döngü riski yok ama boş sayfa
- `limit=100000` → tüm veriyi tek sayfada döndürür (performans sorunu geri gelir)

---

### 9. XSS Riski: Eczane Adı Doğrudan HTML'e Enjekte Ediliyor
**Dosya:** [app.js:228](file:///media/emrehan/HDD/github/Eczanem/static/js/app.js#L228)

```javascript
card.innerHTML = `<h4>${ph.name} ${badge}</h4>`;
```

Eczane adları OSM'den geliyor ve içinde kötü niyetli HTML/JS kodu olabilir. `innerHTML` kullanımı XSS saldırısına açık:
```
Eczane adı: <img src=x onerror=alert('hack')>
```

Aynı sorun popup içeriğinde de var ([app.js:196](file:///media/emrehan/HDD/github/Eczanem/static/js/app.js#L196)).

---

### 10. `import` İfadeleri Dosya Ortasında Dağınık
**Dosya:** [update_data.py:30, 32, 115](file:///media/emrehan/HDD/github/Eczanem/scripts/update_data.py#L30)

```python
# Satır 1-5: import requests, json, os, time
# Satır 30: import math  (kullanılmıyor!)
# Satır 32: import reverse_geocoder as rg
# Satır 115: import concurrent.futures
```

`import math` hiç kullanılmıyor. Diğer importlar dosyanın ortasına serpiştirilmiş.

---

## 📊 Özet Tablosu

| # | Seviye | Sorun | Dosya |
|---|--------|-------|-------|
| 1 | 🔴 Kritik | Stok verileri sahte, her restart'ta değişiyor | `index.py` |
| 2 | 🔴 Kritik | Nöbetçi eşleştirme %67 yanlış pozitif | `update_data.py` |
| 3 | 🔴 Kritik | OSM fallback doğru RG sonucunu eziyor | `update_data.py` |
| 4 | 🟠 Önemli | 5.7 MB JSON filtresiz indiriliyor | `index.py` |
| 5 | 🟠 Önemli | Şehir eşleştirmede substring yanlış pozitif | `update_data.py` |
| 6 | 🟠 Önemli | Şehir değişince kategori filtresi sıfırlanmıyor | `products.html` |
| 7 | 🟡 Orta | Afyon/Maraş kısaltması scraping URL'ini bozabilir | `update_data.py` |
| 8 | 🟡 Orta | Sayfa numarası validasyonu yok | `index.py` |
| 9 | 🟡 Orta | XSS riski (innerHTML ile OSM verisi) | `app.js` |
| 10 | 🟡 Orta | Kullanılmayan import + dağınık importlar | `update_data.py` |
