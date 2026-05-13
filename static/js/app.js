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

// XSS Protection: Escape HTML entities in user-generated content
function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// Counter animation for stats
document.addEventListener('DOMContentLoaded', () => {
    // Animate stat numbers
    const statNums = document.querySelectorAll('.hero-stat-num, .admin-stat-num');
    statNums.forEach(el => {
        const target = parseInt(el.textContent);
        if (isNaN(target) || target === 0) return;
        
        let current = 0;
        const increment = Math.max(1, Math.floor(target / 30));
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            el.textContent = current;
        }, 30);
    });
});
