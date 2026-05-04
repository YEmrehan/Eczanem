/* ─── JS App Logic ───────────────────────────── */

// Toast Notifications
function showToast(message) {
  let toast = document.querySelector('.toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.className = 'toast';
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2500);
}

// Map & List Integration
document.addEventListener('DOMContentLoaded', () => {
    const mapElement = document.getElementById('map');
    if (!mapElement) return;

    // 1. Initialize Map
    const map = L.map('map').setView([41.0082, 28.9784], 11);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);
    map.attributionControl.setPrefix(false);

    // 2. Initialize Marker Cluster Group (Performance)
    const markersGroup = L.markerClusterGroup({
        chunkedLoading: true,
        maxClusterRadius: 50,
        spiderfyOnMaxZoom: true
    });
    map.addLayer(markersGroup);

    // Custom Icons
    const normalIcon = L.divIcon({ className: 'custom-pin normal-pin', html: '💊', iconSize: [26, 26], iconAnchor: [13, 26] });
    const dutyIcon = L.divIcon({ className: 'custom-pin duty-pin', html: '🚨', iconSize: [32, 32], iconAnchor: [16, 32] });

    let allPharmacies = [];
    let currentFiltered = [];
    let displayedCount = 0;
    const PAGE_SIZE = 20;

    // Elements
    const citySelect = document.getElementById('city-selector');
    const districtSelect = document.getElementById('district-selector');
    const nameSearch = document.getElementById('name-search');
    const dutyToggle = document.getElementById('on-duty-filter');
    const listContainer = document.getElementById('pharmacy-list');
    const loadMoreTrigger = document.getElementById('load-more-trigger');
    const listCountBadge = document.getElementById('list-count');

    // 3. Fetch Data
    fetch('/api/pharmacies')
        .then(res => res.json())
        .then(data => {
            allPharmacies = data;
            extractDistricts();
            applyFilters();
            if (citySelect) {
                citySelect.addEventListener('change', () => {
                    extractDistricts();
                    applyFilters();
                });
            }
            if (districtSelect) districtSelect.addEventListener('change', applyFilters);
            if (dutyToggle) dutyToggle.addEventListener('change', applyFilters);
            // Debounce süresini 300'den 600ms'ye çıkararak 24k marker render yükünü hafiflettik
            if (nameSearch) nameSearch.addEventListener('input', debounce(applyFilters, 600));
            
            // Lazy Loading Observer
            setupLazyLoading();
        });

    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    // Extract unique districts from data
    function extractDistricts() {
        if(!districtSelect) return;
        districtSelect.innerHTML = '<option value="">Tüm İlçeler</option>'; // Clear existing
        
        let districts = new Set();
        let selectedCity = citySelect ? citySelect.value : "Tümü";
        let normCity = normalize(selectedCity);
        
        allPharmacies.forEach(p => {
            let matchCity = false;
            if (selectedCity === "Tümü") {
                matchCity = true;
            } else {
                let pCity = normalize(p.city);
                let pAddr = normalize(p.address);
                let pDist = normalize(p.district);
                matchCity = pCity.includes(normCity) || pDist.includes(normCity) || pAddr.includes(normCity);
            }
            
            if (matchCity && p.district) {
                districts.add(p.district);
            }
        });
        
        Array.from(districts).sort().forEach(d => {
            let opt = document.createElement('option');
            opt.value = d;
            opt.textContent = d;
            districtSelect.appendChild(opt);
        });
    }

    function normalize(str) {
        if (!str) return "";
        return str.toLocaleLowerCase('tr-TR')
                  .replace(/ğ/g, 'g').replace(/ü/g, 'u').replace(/ş/g, 's')
                  .replace(/ı/g, 'i').replace(/ö/g, 'o').replace(/ç/g, 'c');
    }

    // Apply Filters
    function applyFilters() {
        let city = citySelect ? citySelect.value : "";
        let dist = districtSelect ? districtSelect.value : "";
        let q = nameSearch ? nameSearch.value.toLowerCase() : "";
        let dutyOnly = dutyToggle ? dutyToggle.checked : false;
        
        let normCity = normalize(city);
        
        currentFiltered = allPharmacies.filter(p => {
            let matchCity = false;
            if (city === "" || city === "Tümü") {
                matchCity = true;
            } else {
                let pCity = normalize(p.city);
                let pAddr = normalize(p.address);
                let pDist = normalize(p.district);
                matchCity = pCity.includes(normCity) || pDist.includes(normCity) || pAddr.includes(normCity);
            }
            
            let matchDist = dist === "" || p.district === dist;
            let matchName = q === "" || p.name.toLowerCase().includes(q) || (p.address && p.address.toLowerCase().includes(q));
            let matchDuty = dutyOnly ? p.on_duty : true;
            return matchCity && matchDist && matchName && matchDuty;
        });
        
        listCountBadge.textContent = currentFiltered.length + " Bulundu";
        
        // Update Map Stats Overlay
        let mapTotalCount = document.getElementById('map-total-count');
        let mapDutyCount = document.getElementById('map-duty-count');
        if (mapTotalCount) mapTotalCount.textContent = currentFiltered.length;
        if (mapDutyCount) {
            let dutyCount = currentFiltered.filter(p => p.on_duty).length;
            mapDutyCount.textContent = dutyCount;
        }
        
        // Reset List & Map
        displayedCount = 0;
        listContainer.innerHTML = "";
        markersGroup.clearLayers();
        
        renderMapMarkers(currentFiltered);
        loadMoreListItems();
        
        // Center Map
        if (currentFiltered.length > 0) {
            const bounds = L.latLngBounds(currentFiltered.map(p => [p.lat, p.lng]));
            map.fitBounds(bounds, { padding: [50, 50], maxZoom: 13 });
        } else {
            if (city !== "Tümü") {
                showToast(city + " için sistemde kayıtlı eczane bulunamadı.");
            }
            map.setView([39.0, 35.0], 6);
        }
    }

    // 5. Render Map
    let mapMarkersDict = {};
    function renderMapMarkers(pharmacies) {
        mapMarkersDict = {}; // [Kritik] Memory Leak engellendi
        const mapMarkers = pharmacies.map(ph => {
            const icon = ph.on_duty ? dutyIcon : normalIcon;
            const marker = L.marker([ph.lat, ph.lng], { icon: icon });
            
            let dutyBadge = ph.on_duty ? `<div style="color:var(--danger); font-weight:bold; font-size:12px; margin-bottom:5px;">🚨 Nöbetçi Eczane</div>` : "";
            
            marker.bindPopup(`
                <div class="map-popup">
                    ${dutyBadge}
                    <h3 style="margin:0 0 5px 0; color:#333; font-size:15px;">${ph.name}</h3>
                    <p style="margin:0 0 10px 0; font-size:12px; color:#666;">${ph.address}</p>
                    <a href="/urunler?pharmacy=${ph.id}" style="display:inline-block; margin-top:5px; padding:5px 10px; background:var(--primary); color:white; border-radius:4px; text-decoration:none; font-size:12px; font-weight:bold;">Stokları Gör</a>
                </div>
            `);
            mapMarkersDict[ph.id] = marker;
            return marker;
        });
        markersGroup.addLayers(mapMarkers);
    }

    // 6. Pagination List (Click to Load More)
    function setupLazyLoading() {
        if(loadMoreTrigger) {
            loadMoreTrigger.addEventListener('click', () => {
                if (displayedCount < currentFiltered.length) {
                    loadMoreListItems();
                }
            });
        }
    }

    function loadMoreListItems() {
        let fragment = document.createDocumentFragment();
        let end = Math.min(displayedCount + PAGE_SIZE, currentFiltered.length);
        
        for (let i = displayedCount; i < end; i++) {
            let ph = currentFiltered[i];
            let card = document.createElement('div');
            card.className = 'pharmacy-list-card';
            let badge = ph.on_duty ? `<span style="color:var(--danger); font-size:0.75rem; font-weight:bold;">🚨 Nöbetçi</span>` : '';
            card.innerHTML = `
                <h4>${ph.name} ${badge}</h4>
                <p>${ph.address || 'Adres bilgisi yok'}</p>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:0.8rem; color:var(--primary)">📍 Haritada Bul</span>
                    <a href="/urunler?pharmacy=${ph.id}" class="badge" style="text-decoration:none; background:var(--bg-card); color:var(--text); border:1px solid var(--border);">Stok Gör</a>
                </div>
            `;
            // Click to center map and open popup
            card.addEventListener('click', (e) => {
                if(e.target.tagName !== 'A') {
                    let m = mapMarkersDict[ph.id];
                    if (m) {
                        markersGroup.zoomToShowLayer(m, () => {
                            m.openPopup();
                        });
                    }
                }
            });
            fragment.appendChild(card);
        }
        
        listContainer.appendChild(fragment);
        displayedCount = end;
        
        if (displayedCount >= currentFiltered.length) {
            loadMoreTrigger.style.display = 'none';
        } else {
            loadMoreTrigger.style.display = 'block';
        }
    }

    // Fix map rendering issues on resize/mobile orientation change
    window.addEventListener('resize', debounce(() => {
        if(map) {
            map.invalidateSize();
        }
    }, 250));
});
