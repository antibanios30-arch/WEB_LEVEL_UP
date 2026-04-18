function toggleMenu() {
    const menu = document.getElementById('mobileMenu');
    menu.classList.toggle('open');
}

// Auto-dismiss flash messages
setTimeout(() => {
    document.querySelectorAll('.flash').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateX(100px)';
        el.style.transition = 'all 0.4s';
        setTimeout(() => el.remove(), 400);
    });
}, 5000);

// Animate numbers
function animateNumber(el, target, duration = 2000) {
    const start = 0;
    const step = target / (duration / 16);
    let current = start;
    const timer = setInterval(() => {
        current += step;
        if (current >= target) {
            current = target;
            clearInterval(timer);
        }
        el.textContent = Math.floor(current).toLocaleString();
    }, 16);
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-count]').forEach(el => {
        const target = parseInt(el.getAttribute('data-count'));
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateNumber(el, target);
                    observer.unobserve(el);
                }
            });
        });
        observer.observe(el);
    });
});

// Tabs
function switchTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
    document.getElementById(tabId).classList.add('active');
}

// Copy token
function copyToken(token) {
    navigator.clipboard.writeText(token).then(() => {
        showToast('تم نسخ التوكن!', 'success');
    });
}

function showToast(msg, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `flash flash-${type}`;
    toast.style.cssText = 'position:fixed;top:90px;right:1.5rem;z-index:9999;animation:slide-in 0.4s ease;max-width:300px;';
    toast.innerHTML = `<i class="fas fa-${type === 'success' ? 'check' : 'times'}-circle"></i> ${msg}`;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        toast.style.transition = 'all 0.4s';
        setTimeout(() => toast.remove(), 400);
    }, 3000);
}

// Admin functions
function completeOrder(id) {
    if (!confirm('تأكيد إتمام الطلب؟')) return;
    fetch(`/admin/order/${id}/complete`, { method: 'POST' })
        .then(r => r.json())
        .then(d => { if (d.success) { showToast('تم!'); location.reload(); } });
}

function toggleUser(id) {
    fetch(`/admin/toggle_user/${id}`, { method: 'POST' })
        .then(r => r.json())
        .then(d => { if (d.success) location.reload(); });
}

function addToken() {
    const uid = document.getElementById('tokenUid').value;
    const token = document.getElementById('tokenVal').value;
    const region = document.getElementById('tokenRegion').value;
    const owner = document.getElementById('tokenOwner').value;
    if (!uid || !token) { showToast('UID والتوكن مطلوبان', 'error'); return; }
    fetch('/admin/add_token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ uid, token, region, owner_id: owner || null })
    }).then(r => r.json())
      .then(d => {
          if (d.success) { showToast('تم إضافة التوكن!'); location.reload(); }
          else showToast(d.error || 'خطأ', 'error');
      });
}
