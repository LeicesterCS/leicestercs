'use strict';

// ─── NAVBAR SCROLL ────────────────────────────
window.addEventListener('scroll', () => {
  document.getElementById('navbar').classList.toggle('scrolled', window.scrollY > 20);
}, { passive: true });

// ─── HAMBURGER ────────────────────────────────
let menuOpen = false;
const ham = document.getElementById('hamburger');
const mob = document.getElementById('mobileMenu');

ham.addEventListener('click', () => {
  menuOpen = !menuOpen;
  mob.classList.toggle('open', menuOpen);
  const [a, b, c] = ham.querySelectorAll('span');
  if (menuOpen) {
    a.style.transform = 'rotate(45deg) translate(4.5px, 4.5px)';
    b.style.opacity = '0';
    c.style.transform = 'rotate(-45deg) translate(4.5px, -4.5px)';
  } else {
    [a, b, c].forEach(s => { s.style.transform = ''; s.style.opacity = ''; });
  }
});

document.querySelectorAll('.mm-link').forEach(l => l.addEventListener('click', () => {
  menuOpen = false;
  mob.classList.remove('open');
  ham.querySelectorAll('span').forEach(s => { s.style.transform = ''; s.style.opacity = ''; });
}));

// ─── ACTIVE NAV LINK (highlight current page) ─
(function () {
  const path = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a, .mm-link').forEach(a => {
    const href = a.getAttribute('href');
    if (href === path || (path === 'index.html' && href === 'index.html')) {
      a.classList.add('active');
    }
  });
})();

// ─── TEAM CARD FLIP ───────────────────────────
document.querySelectorAll('.tc-flip-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const card = document.getElementById(btn.dataset.card);
    if (!card) return;
    const flipped = card.classList.toggle('flipped');
    btn.textContent = flipped ? 'BACK ↺' : 'FLIP ↺';
    btn.classList.toggle('active', flipped);
  });
});

// ─── INTERACTIVE ENHANCEMENTS ───────────────────────────
// Loading state for forms
function showLoading(element) {
  element.classList.add('loading');
}

function hideLoading(element) {
  element.classList.remove('loading');
}

// Toast notifications
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container') || createToastContainer();
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-mark">${type === 'success' ? '✓' : '✗'}</span>
    <span class="toast-text">${message}</span>
  `;
  container.appendChild(toast);
  setTimeout(() => toast.classList.add('toast-in'), 10);
  setTimeout(() => {
    toast.classList.remove('toast-in');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function createToastContainer() {
  const container = document.createElement('div');
  container.id = 'toast-container';
  document.body.appendChild(container);
  return container;
}

// Enhanced form submissions with loading
document.addEventListener('DOMContentLoaded', () => {
  // Ideas form
  const ideasForm = document.getElementById('ideaForm');
  if (ideasForm) {
    ideasForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      showLoading(ideasForm);
      const formData = new FormData(ideasForm);
      const data = {
        name: formData.get('name') || 'Anonymous',
        category: formData.get('type') || 'General',
        idea: formData.get('idea')
      };
      try {
        const response = await fetch('/api/submit_ideas', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data)
        });
        const result = await response.json();
        showToast(result.message, response.ok ? 'success' : 'error');
        if (response.ok) ideasForm.reset();
      } catch (error) {
        showToast('Failed to submit idea', 'error');
      }
      hideLoading(ideasForm);
    });
  }

  // Add fade-in to dynamic content
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('fade-in');
      }
    });
  });
  document.querySelectorAll('.event-row').forEach(el => observer.observe(el));
});

// ─── PARTNER SCROLL GLOW ──────────────────────
const partnerObs = new IntersectionObserver(entries => {
  entries.forEach(e => e.target.classList.toggle('in-view', e.isIntersecting));
}, { threshold: 0.6 });
document.querySelectorAll('.partner').forEach(p => partnerObs.observe(p));

// ─── PARTNERS MARQUEE DUPLICATION ────────────
const track = document.querySelector('.marquee-track');
if (track) {
  const content = track.innerHTML;
  track.innerHTML += content + content + content;
}

// ─── TOAST NOTIFICATION ───────────────────────
function showToast(message, duration = 3500, isError = false) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = 'toast' + (isError ? ' toast-error' : '');
  toast.innerHTML = `<span class="toast-mark">${isError ? '✗' : '✓'}</span><span class="toast-msg">${message}</span>`;
  container.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add('toast-in'));
  setTimeout(() => {
    toast.classList.remove('toast-in');
    toast.addEventListener('transitionend', () => toast.remove(), { once: true });
  }, duration);
}

// ─── IDEAS FORM ───────────────────────────────
const ideaForm = document.getElementById('ideaForm');
if (ideaForm) {
  ideaForm.addEventListener('submit', async function (e) {
    e.preventDefault();
    const btn = document.getElementById('ideaBtn');
    const name = document.getElementById('ideaName')?.value || 'Anonymous';
    const category = document.getElementById('ideaCategory')?.value || 'General';
    const idea = document.getElementById('ideaText')?.value;
    
    btn.textContent = 'SENDING...';
    btn.disabled = true;
    
    try {
      const response = await fetch('/api/submit_ideas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, category, idea })
      });
      
      if (response.ok) {
        btn.textContent = 'SUBMIT';
        btn.disabled = false;
        this.reset();
        showToast('IDEA RECEIVED. THE COMMITTEE WILL TAKE A LOOK.');
      } else {
        throw new Error('Server error');
      }
    } catch (err) {
      // DEMO MODE: Show success even without server (remove this catch block when server is running)
      btn.textContent = 'SUBMIT';
      btn.disabled = false;
      this.reset();
      showToast('IDEA RECEIVED. THE COMMITTEE WILL TAKE A LOOK.');
      console.log('Demo mode: Simulated successful submission. Remove this catch block when server is running.');
    }
  });
}

// ─── PHOTO LIGHTBOX ───────────────────────────
(function () {
  const tiles = document.querySelectorAll('.gm-tile');
  if (!tiles.length) return;

  // Build overlay
  const overlay = document.createElement('div');
  overlay.id = 'lightbox';
  overlay.innerHTML = `
    <div class="lb-backdrop"></div>
    <button class="lb-close" aria-label="Close">✕</button>
    <button class="lb-prev" aria-label="Previous">‹</button>
    <button class="lb-next" aria-label="Next">›</button>
    <div class="lb-content">
      <img class="lb-img" src="" alt="" />
      <div class="lb-label"></div>
    </div>`;
  document.body.appendChild(overlay);

  const lbImg   = overlay.querySelector('.lb-img');
  const lbLabel = overlay.querySelector('.lb-label');

  // Collect all tiles that have an img
  const items = [...tiles].map(t => ({
    src:   t.querySelector('img')?.src   || '',
    alt:   t.querySelector('img')?.alt   || '',
    label: t.querySelector('.gm-label')?.textContent || ''
  })).filter(i => i.src);

  let current = 0;

  function open(idx) {
    current = (idx + items.length) % items.length;
    lbImg.src        = items[current].src;
    lbImg.alt        = items[current].alt;
    lbLabel.textContent = items[current].label;
    overlay.classList.add('lb-open');
    document.body.style.overflow = 'hidden';
  }

  function close() {
    overlay.classList.remove('lb-open');
    document.body.style.overflow = '';
  }

  tiles.forEach((tile, i) => {
    if (!tile.querySelector('img')) return;
    tile.style.cursor = 'pointer';
    tile.addEventListener('click', () => open(i));
  });

  overlay.querySelector('.lb-close').addEventListener('click', close);
  overlay.querySelector('.lb-backdrop').addEventListener('click', close);
  overlay.querySelector('.lb-prev').addEventListener('click', (e) => { e.stopPropagation(); open(current - 1); });
  overlay.querySelector('.lb-next').addEventListener('click', (e) => { e.stopPropagation(); open(current + 1); });

  document.addEventListener('keydown', e => {
    if (!overlay.classList.contains('lb-open')) return;
    if (e.key === 'Escape')      close();
    if (e.key === 'ArrowLeft')   open(current - 1);
    if (e.key === 'ArrowRight')  open(current + 1);
  });
})();

// ─── DISCORD WIDGET ───────────────────────────
(function () {
  const widget = document.getElementById('discord-widget');
  if (!widget) return;

  const GUILD_ID = '939530345248874496';

  fetch(`https://discord.com/api/guilds/${GUILD_ID}/widget.json`)
    .then(r => r.json())
    .then(data => {
      const onlineEl  = document.getElementById('dw-online');
      const nameEl    = document.getElementById('dw-name');
      if (onlineEl) onlineEl.textContent = data.presence_count ?? '—';
      if (nameEl)   nameEl.textContent   = data.name ?? 'LeicesterCS';
      widget.classList.add('dw-loaded');
    })
    .catch(() => {
      
    });
})();

// ─── FAQ ACCORDION ────────────────────────────
document.querySelectorAll('.faq-item').forEach(item => {
  const btn = item.querySelector('.faq-q');
  const ans = item.querySelector('.faq-a');
  if (!btn || !ans) return;
  btn.addEventListener('click', () => {
    const open = item.classList.toggle('faq-open');
    btn.setAttribute('aria-expanded', open);
    ans.style.maxHeight = open ? ans.scrollHeight + 'px' : '0';
  });
});
