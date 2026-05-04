/* ─── Counter Animation ─────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const counters = document.querySelectorAll('[data-count]');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        animateCounter(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });
  counters.forEach(el => observer.observe(el));
});

function animateCounter(el) {
  const target = parseInt(el.dataset.count);
  const duration = 1200;
  const start = performance.now();
  function tick(now) {
    const progress = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.floor(ease * target);
    if (progress < 1) requestAnimationFrame(tick);
    else el.textContent = target;
  }
  requestAnimationFrame(tick);
}

/* ─── Toast ─────────────────────────────────────── */
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

/* ─── Map Integration ───────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
    const mapElement = document.getElementById('map');
    if (!mapElement) return; // Only run on map page

    // Initialize map centered on Turkey
    const map = L.map('map').setView([39.0, 35.0], 6);

    // Dark theme tiles
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);

    let markers = [];

    // Custom icons
    const normalIcon = L.divIcon({
        className: 'custom-pin normal-pin',
        html: '💊',
        iconSize: [30, 30],
        iconAnchor: [15, 30]
    });

    const dutyIcon = L.divIcon({
        className: 'custom-pin duty-pin',
        html: '🚨',
        iconSize: [36, 36],
        iconAnchor: [18, 36]
    });

    // Fetch and render pharmacies
    fetch('/api/pharmacies')
        .then(res => res.json())
        .then(data => {
            renderMarkers(data);

            // Filter toggle
            const toggle = document.getElementById('on-duty-filter');
            if(toggle) {
                toggle.addEventListener('change', (e) => {
                    if (e.target.checked) {
                        const filtered = data.filter(p => p.on_duty);
                        renderMarkers(filtered);
                    } else {
                        renderMarkers(data);
                    }
                });
            }
        });

    function renderMarkers(pharmacies) {
        // Clear existing markers
        markers.forEach(m => map.removeLayer(m));
        markers = [];

        pharmacies.forEach(ph => {
            const icon = ph.on_duty ? dutyIcon : normalIcon;
            const marker = L.marker([ph.lat, ph.lng], { icon: icon }).addTo(map);
            
            let dutyBadge = ph.on_duty ? `<div style="color:var(--danger); font-weight:bold; font-size:12px; margin-bottom:5px;">Nöbetçi Eczane</div>` : "";
            
            marker.bindPopup(`
                <div class="map-popup">
                    ${dutyBadge}
                    <h3 style="margin:0 0 5px 0; color:#333;">${ph.name}</h3>
                    <p style="margin:0 0 10px 0; font-size:12px; color:#666;">${ph.address}</p>
                    <a href="/urunler?pharmacy=${ph.id}" style="display:inline-block; padding:5px 10px; background:var(--primary); color:white; border-radius:4px; text-decoration:none; font-size:13px; font-weight:bold;">Stokları Gör</a>
                </div>
            `);
            markers.push(marker);
        });
    }
});
