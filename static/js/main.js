(function () {
  'use strict';

  const btn = document.getElementById('mobile-menu-btn');
  const menu = document.getElementById('mobile-menu');
  const closeBtn = document.getElementById('mobile-menu-close');
  if (!btn || !menu) return;

  const hamburger = btn.querySelector('.hamburger-icon');
  const close = btn.querySelector('.close-icon');

  document.head.insertAdjacentHTML('beforeend', `<style>
    #mobile-menu{
      position:fixed;inset:0;z-index:45;
      background:#ffffff;
      transform-origin:top right;
      transform:perspective(1200px) rotateY(90deg);
      opacity:0;
      pointer-events:none;
      transition:transform .5s cubic-bezier(.4,0,.2,1),opacity .5s cubic-bezier(.4,0,.2,1);
      overflow-y:auto;
    }
    #mobile-menu.open{
      transform:perspective(1200px) rotateY(0deg);
      opacity:1;
      pointer-events:auto;
    }
    #mobile-menu.closing{
      transform:perspective(1200px) rotateY(90deg);
      opacity:0;
      pointer-events:none;
    }
  `);

  let animating = false;

  function openMenu() {
    if (animating) return;
    animating = true;
    menu.classList.remove('closing','hidden');
    hamburger.classList.add('hidden');
    close.classList.remove('hidden');
    btn.setAttribute('aria-expanded','true');
    void menu.offsetWidth;
    menu.classList.add('open');
    setTimeout(function(){ animating = false; }, 520);
  }

  function closeMenu() {
    if (animating) return;
    animating = true;
    menu.classList.remove('open');
    menu.classList.add('closing');
    hamburger.classList.remove('hidden');
    close.classList.add('hidden');
    btn.setAttribute('aria-expanded','false');
    setTimeout(function(){
      menu.classList.add('hidden');
      menu.classList.remove('closing');
      animating = false;
    }, 520);
  }

  btn.addEventListener('click', function () {
    if (menu.classList.contains('open')) {
      closeMenu();
    } else {
      openMenu();
    }
  });

  if (closeBtn) {
    closeBtn.addEventListener('click', closeMenu);
  }
})();


/* ============================================================
   Testimonials — Animation flottante (monte/descend)
   ============================================================ */
(function () {
    'use strict';

    var grid = document.querySelector('[data-testimonials-grid]');
    if (!grid) return;

    var cards = grid.querySelectorAll('.testimonial-card');
    if (!cards.length) return;

    /* Respect de prefers-reduced-motion : on ne fait rien si l'utilisateur a désactivé les animations */
    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduceMotion) return;

    /* Injection des keyframes une seule fois */
    if (!document.getElementById('autolink-testimonial-float-style')) {
        var style = document.createElement('style');
        style.id = 'autolink-testimonial-float-style';
        style.textContent = [
            '@keyframes testimonialFloatUp {',
            '    0%, 100% { transform: translateY(0); }',
            '    50%      { transform: translateY(-10px); }',
            '}',
            '.testimonial-card.is-floating {',
            '    animation: testimonialFloatUp var(--float-duration, 6s) ease-in-out infinite;',
            '    animation-delay: var(--float-delay, 0s);',
            '    will-change: transform;',
            '}',
            /* Pause de l'animation au survol pour ne pas gêner la lecture */
            '.testimonial-card.is-floating:hover {',
            '    animation-play-state: paused;',
            '}'
        ].join('\n');
        document.head.appendChild(style);
    }

    /* Attribution des délais et durées — un pattern différent par carte */
    var delays = [0, 0.6, 1.2, 0.3, 0.9, 1.5];
    var durations = [6, 6.5, 7, 6.2, 6.8, 7.4];

    cards.forEach(function (card, index) {
        var i = index % delays.length;
        card.style.setProperty('--float-delay', delays[i] + 's');
        card.style.setProperty('--float-duration', durations[i] + 's');
    });

    /* Démarrer l'animation quand la grille devient visible (IntersectionObserver) */
    if ('IntersectionObserver' in window) {
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    cards.forEach(function (card) {
                        card.classList.add('is-floating');
                    });
                    observer.disconnect();
                }
            });
        }, { threshold: 0.15 });

        observer.observe(grid);
    } else {
        /* Fallback : démarrer immédiatement */
        cards.forEach(function (card) {
            card.classList.add('is-floating');
        });
    }
})();



// =============================================
// Animation des étapes "Comment ça marche" AU SCROLL
// =============================================
document.addEventListener('DOMContentLoaded', function() {
    // Sélectionne la section et les étapes
    const section = document.querySelector('section[aria-labelledby="how-heading"]');
    const step1 = document.querySelector('.step-1');
    const step2 = document.querySelector('.step-2');
    const step3 = document.querySelector('.step-3');

    if (!section || !step1 || !step2 || !step3) return;

    // Position initiale (masquée)
    step1.style.opacity = '0';
    step1.style.transform = 'translateX(50px)';

    step2.style.opacity = '0';
    step2.style.transform = 'translateX(-50px)';

    step3.style.opacity = '0';
    step3.style.transform = 'translateY(50px)';

    // Crée un observateur pour détecter quand la section est visible à 20%
    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    // Animation pour l'étape 1 (vient de la droite)
                    setTimeout(() => {
                        step1.style.opacity = '1';
                        step1.style.transform = 'translateX(0)';
                        step1.style.transition = 'all 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
                    }, 100);

                    // Animation pour l'étape 2 (vient de la gauche)
                    setTimeout(() => {
                        step2.style.opacity = '1';
                        step2.style.transform = 'translateX(0)';
                        step2.style.transition = 'all 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
                    }, 300);

                    // Animation pour l'étape 3 (vient du bas)
                    setTimeout(() => {
                        step3.style.opacity = '1';
                        step3.style.transform = 'translateY(0)';
                        step3.style.transition = 'all 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
                    }, 500);

                    // Arrête l'observation une fois les animations déclenchées
                    observer.unobserve(entry.target);
                }
            });
        },
        {
            threshold: 0.2, // Déclenche quand 20% de la section est visible
            rootMargin: '0px 0px -50px 0px' // Déclenche 50px avant que la section n'atteigne le bas de l'écran
        }
    );

    // Observe la section
    observer.observe(section);
});


/* =========================================================
   Recherche de mécaniciens — contrôleur du bloc #search-controls
   ========================================================= */
document.addEventListener('DOMContentLoaded', () => {
    const btn      = document.getElementById('find-nearby-btn');
    const btnText  = document.getElementById('find-nearby-btn-text');
    const statusEl = document.getElementById('search-status');
    const progress = document.getElementById('search-progress');
    const radiusEl = document.getElementById('radius-select');
    const availEl  = document.getElementById('available-filter');

    if (!btn) return; // sécurité si le bloc n'est pas sur la page

    /* ---------- Libellés (traduits via data-attributes) ---------- */
    const LABELS = {
        idle:    btn.dataset.labelIdle    || 'Lancer la recherche',
        loading: btn.dataset.labelLoading || 'Recherche en cours…',
        success: btn.dataset.labelSuccess || 'Recherche terminée',
    };

    const ICONS = {
        idle:    btn.querySelector('[data-icon="idle"]'),
        loading: btn.querySelector('[data-icon="loading"]'),
        success: btn.querySelector('[data-icon="success"]'),
    };

    /* ---------- Styles de la zone de statut ---------- */
    const STATUS_STYLES = {
        info:    'border-navy-500/20 bg-navy-500/5 text-navy-900',
        success: 'border-emerald-200 bg-emerald-50 text-emerald-800',
        error:   'border-red-200 bg-red-50 text-red-700',
    };

    const STATUS_ICONS = {
        info: `<svg class="h-5 w-5 shrink-0 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                   <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                   <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
               </svg>`,
        success: `<svg class="h-5 w-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>`,
        error: `<svg class="h-5 w-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
                </svg>`,
    };

    /* ---------- Affiche / masque le message de statut ---------- */
    function showStatus(message, type = 'info') {
        if (!statusEl) return;
        statusEl.className =
            `mt-4 flex items-start gap-3 rounded-xl border px-4 py-3 text-sm font-medium transition-all duration-300 ${STATUS_STYLES[type] || STATUS_STYLES.info}`;
        statusEl.innerHTML = `${STATUS_ICONS[type] || STATUS_ICONS.info}<span class="flex-1" data-status-text></span>`;
        statusEl.querySelector('[data-status-text]').textContent = message;
        statusEl.classList.remove('hidden');
    }

    function hideStatus() {
        if (statusEl) statusEl.classList.add('hidden');
    }

    /* ---------- État de chargement global (overlay AutoLink) ---------- */
    function showGlobalLoader(title) {
        if (window.AutoLink && typeof window.AutoLink.showLoading === 'function') {
            window.AutoLink.showLoading(title);
        }
    }

    function hideGlobalLoader() {
        if (window.AutoLink && typeof window.AutoLink.hideLoading === 'function') {
            window.AutoLink.hideLoading();
        }
    }

    /* ---------- Change l'état visuel du bouton ---------- */
    function setState(state) {
        btn.dataset.state = state;
        btn.disabled = state === 'loading';
        btn.setAttribute('aria-busy', state === 'loading' ? 'true' : 'false');

        if (btnText) btnText.textContent = LABELS[state] || LABELS.idle;

        Object.entries(ICONS).forEach(([key, el]) => {
            if (el) el.classList.toggle('hidden', key !== state);
        });

        if (progress) progress.classList.toggle('hidden', state !== 'loading');
    }

    /* ---------- (Optionnel) récupération de la position ---------- */
    function getPosition() {
        return new Promise((resolve) => {
            if (!navigator.geolocation) return resolve(null);
            navigator.geolocation.getCurrentPosition(
                (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
                () => resolve(null),
                { enableHighAccuracy: true, timeout: 8000 }
            );
        });
    }

    /* ---------- Requête réelle vers votre API ---------- */
    async function fetchMechanics({ radius, available, coords }) {
        const params = new URLSearchParams({ radius, available: available ? '1' : '0' });
        if (coords) {
            params.set('lat', coords.lat);
            params.set('lng', coords.lng);
        }

        const response = await fetch(`/api/mechanics/search/?${params.toString()}`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        return {
            count: data.count ?? (data.results ? data.results.length : 0),
            results: data.results || data,
        };
    }

    /* ---------- Clic sur le bouton ---------- */
    btn.addEventListener('click', async () => {
        if (btn.disabled) return;

        setState('loading');
        showGlobalLoader('Recherche de mécaniciens à proximité…');
        showStatus('Recherche des mécaniciens autour de vous…', 'info');

        try {
            const radius    = radiusEl ? radiusEl.value : '5';
            const available = availEl ? availEl.checked : false;
            const coords    = await getPosition();

            const { count, results } = await fetchMechanics({ radius, available, coords });

            setState('success');
            hideGlobalLoader();

            if (count > 0) {
                showStatus(
                    `${count} mécanicien${count > 1 ? 's' : ''} trouvé${count > 1 ? 's' : ''} dans un rayon de ${radius} km.`,
                    'success'
                );
            } else {
                showStatus(
                    `Aucun mécanicien trouvé dans un rayon de ${radius} km. Essayez d'élargir votre recherche.`,
                    'error'
                );
            }

            // Permet à la liste de résultats d'écouter et de se mettre à jour
            document.dispatchEvent(new CustomEvent('mechanics:results', {
                detail: { count, results, radius: Number(radius), available, coords },
            }));

            // Retour à l'état initial après 2,5 s
            setTimeout(() => {
                if (btn.dataset.state === 'success') setState('idle');
            }, 2500);

        } catch (error) {
            console.error('[Recherche mécaniciens]', error);
            hideGlobalLoader();
            setState('idle');
            showStatus("Une erreur est survenue pendant la recherche. Veuillez réessayer.", 'error');
        }
    });

    /* ---------- Réinitialise le message si l'utilisateur change un filtre ---------- */
    [radiusEl, availEl].forEach((el) => {
        el?.addEventListener('change', () => {
            if (btn.dataset.state === 'idle') hideStatus();
        });
    });
});