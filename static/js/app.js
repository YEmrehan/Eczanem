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

/* ─── Live Search ───────────────────────────────── */
const heroInput = document.getElementById('hero-search-input');
const heroResults = document.getElementById('hero-search-results');
let debounceTimer;

if (heroInput && heroResults) {
  heroInput.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const q = heroInput.value.trim();
    if (q.length < 2) { heroResults.classList.remove('active'); return; }
    debounceTimer = setTimeout(() => fetchResults(q), 250);
  });

  heroInput.addEventListener('blur', () => {
    setTimeout(() => heroResults.classList.remove('active'), 200);
  });
}

async function fetchResults(query) {
  try {
    const res = await fetch(`/api/products?search=${encodeURIComponent(query)}`);
    const data = await res.json();
    if (!data.length) { heroResults.classList.remove('active'); return; }
    heroResults.innerHTML = data.slice(0, 5).map(p => `
      <a href="/urunler?search=${encodeURIComponent(p.name)}" class="search-result-item">
        <span class="search-result-name">${p.category_info.icon} ${p.name}</span>
        <span class="search-result-price">₺${p.price.toFixed(2)}</span>
      </a>
    `).join('');
    heroResults.classList.add('active');
  } catch (e) {
    console.error('Search error:', e);
  }
}

/* ─── Admin Tabs ────────────────────────────────── */
function switchTab(tabName) {
  document.querySelectorAll('.admin-panel').forEach(p => p.classList.add('hidden'));
  document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
  const panel = document.getElementById('tab-' + tabName);
  if (panel) panel.classList.remove('hidden');
  event.currentTarget.classList.add('active');
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

/* ─── Add to Cart (demo) ────────────────────────── */
function addToCart(productName) {
  showToast(`✅ ${productName} sepete eklendi!`);
}
