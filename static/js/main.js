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
      background:#00002B;
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