// Mobile helper script for UOGA Hunt Builder
(function () {
  'use strict';

  // Add "is-mobile" class on small screens
  function updateViewportClass() {
    if (window.innerWidth <= 767) {
      document.documentElement.classList.add('is-mobile');
    } else {
      document.documentElement.classList.remove('is-mobile');
    }
  }

  // Toggle utility nav if a hamburger exists or create one
  function ensureMobileNavToggle() {
    const topbar = document.querySelector('.topbar');
    if (!topbar) return;

    // If a toggle already exists, skip
    if (document.querySelector('.mobile-nav-toggle')) return;

    const controls = topbar.querySelector('.controls') || topbar;
    const btn = document.createElement('button');
    btn.className = 'mobile-nav-toggle';
    btn.type = 'button';
    btn.setAttribute('aria-expanded', 'false');
    btn.setAttribute('aria-label', 'Open site menu');
    btn.textContent = 'Menu';
    btn.style.marginLeft = '8px';

    // Insert to the right side of the topbar controls
    controls.insertBefore(btn, controls.firstChild);

    const nav = document.querySelector('.utility-nav');
    if (!nav) return;
    nav.classList.remove('open');

    btn.addEventListener('click', () => {
      const open = nav.classList.toggle('open');
      btn.setAttribute('aria-expanded', String(open));
    });
  }

  // Make images lazy if not explicitly set (non-invasive)
  function setLazyImages() {
    try {
      document.querySelectorAll('img').forEach(img => {
        if (!img.hasAttribute('loading')) {
          img.setAttribute('loading', 'lazy');
        }
      });
    } catch (e) {
      // ignore
    }
  }

  // Small helper to find overflow-causing elements (call from console: uogaFindOverflow())
  window.uogaFindOverflow = function () {
    const w = document.documentElement.clientWidth;
    const over = Array.from(document.querySelectorAll('*')).filter(el => {
      const r = el.getBoundingClientRect();
      return r.right > w + 1;
    }).map(el => {
      return {
        tag: el.tagName,
        classes: el.className,
        right: Math.round(el.getBoundingClientRect().right),
        width: el.offsetWidth
      };
    });
    // Log to console
    console.table(over.slice(0, 200));
    return over;
  };

  // Init on DOM ready
  document.addEventListener('DOMContentLoaded', () => {
    updateViewportClass();
    ensureMobileNavToggle();
    setLazyImages();
  });

  window.addEventListener('resize', updateViewportClass);
})();
