/**
 * AutoLink — État de chargement global
 * ---------------------------------------------------------------
 * Reprend l'état de chargement du formulaire « Ajouter un garage »
 * (overlay plein écran : spinner + message) et l'applique à TOUS les
 * formulaires et liens de l'application :
 *   - overlay identique à celui du garage (spinner + titre + sous-titre),
 *   - bouton de soumission désactivé avec spinner intégré.
 *
 * Les traitements AJAX (fetch) gardent leur propre état de chargement :
 * tout évènement déjà `preventDefault()` est ignoré, ainsi que les
 * éléments marqués `data-no-loading`.
 *
 * Personnalisation :
 *   - window.AL_LOADING = { title, subtitle }   (défini dans les bases)
 *   - data-loading-text="..."                   sur un <form> ou un <a>
 *   - data-no-loading                           sur un <form>, <a> ou conteneur
 *   - window.AutoLink.showLoading(title, subtitle) / hideLoading()
 */
(function () {
    'use strict';

    window.AutoLink = window.AutoLink || {};

    var CONFIG = window.AL_LOADING || {};
    var DEFAULT_TITLE = CONFIG.title || 'Chargement en cours…';
    var DEFAULT_SUBTITLE = CONFIG.subtitle || 'Veuillez patienter un instant.';

    // Filet de sécurité : si la navigation n'a pas lieu (téléchargement, lien
    // bloqué…), on ne laisse jamais l'overlay affiché indéfiniment.
    var NAV_SAFETY_MS = 30000;

    var overlay = null;
    var titleEl = null;
    var subtitleEl = null;
    var timer = null;
    var pending = []; // boutons dont l'état a été modifié

    var SPINNER_OVERLAY =
        '<svg class="w-8 h-8 text-emerald-600 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">' +
        '<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>' +
        '<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>' +
        '</svg>';

    var SPINNER_BUTTON =
        '<svg class="w-4 h-4 mr-2 inline-block align-middle animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">' +
        '<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>' +
        '<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>' +
        '</svg>';

    // ==========================================
    // OVERLAY
    // ==========================================
    function buildOverlay() {
        if (overlay && document.body.contains(overlay)) return overlay;

        overlay = document.createElement('div');
        overlay.id = 'al-loading-overlay';
        overlay.setAttribute('role', 'status');
        overlay.setAttribute('aria-live', 'polite');
        overlay.setAttribute('aria-hidden', 'true');
        overlay.className = 'fixed inset-0 z-[200] hidden items-center justify-center bg-black/60 backdrop-blur-sm';
        overlay.innerHTML =
            '<div class="bg-white rounded-2xl shadow-2xl p-8 sm:p-10 max-w-sm w-full mx-4 text-center">' +
                '<div class="w-16 h-16 mx-auto mb-4 rounded-full bg-emerald-100 flex items-center justify-center">' +
                    SPINNER_OVERLAY +
                '</div>' +
                '<h3 class="al-loading-title text-lg font-bold text-navy-900 mb-2"></h3>' +
                '<p class="al-loading-subtitle text-sm text-graphite-500"></p>' +
            '</div>';

        document.body.appendChild(overlay);
        titleEl = overlay.querySelector('.al-loading-title');
        subtitleEl = overlay.querySelector('.al-loading-subtitle');

        return overlay;
    }

    function showLoading(title, subtitle) {
        buildOverlay();
        titleEl.textContent = title || DEFAULT_TITLE;
        subtitleEl.textContent = subtitle || DEFAULT_SUBTITLE;
        overlay.classList.remove('hidden');
        overlay.classList.add('flex');
        overlay.setAttribute('aria-hidden', 'false');
        document.documentElement.style.cursor = 'progress';
    }

    function restoreButtons() {
        pending.forEach(function (item) {
            if (item.kind === 'input') {
                item.el.value = item.value;
            } else {
                item.el.innerHTML = item.value;
            }
            item.el.disabled = item.disabled;
            item.el.removeAttribute('aria-busy');
            delete item.el.dataset.alLoading;
        });
        pending = [];
    }

    function hideLoading() {
        if (timer) { clearTimeout(timer); timer = null; }
        if (overlay) {
            overlay.classList.add('hidden');
            overlay.classList.remove('flex');
            overlay.setAttribute('aria-hidden', 'true');
        }
        document.documentElement.style.cursor = '';
        restoreButtons();
    }
    // ==========================================
    // BOUTONS
    // ==========================================
    function setButtonLoading(btn) {
        if (!btn || btn.dataset.alLoading === '1') return;

        if (btn.tagName === 'INPUT') {
            pending.push({ el: btn, kind: 'input', value: btn.value, disabled: btn.disabled });
            btn.value = btn.dataset.loadingText || btn.value;
        } else {
            var label = (btn.dataset.loadingText || btn.textContent || '').trim();
            pending.push({ el: btn, kind: 'button', value: btn.innerHTML, disabled: btn.disabled });
            btn.innerHTML = SPINNER_BUTTON + (label ? '<span>' + label + '</span>' : '');
        }

        btn.disabled = true;
        btn.dataset.alLoading = '1';
        btn.setAttribute('aria-busy', 'true');
    }

    function findSubmitButton(form) {
        var btn = form.querySelector('button[type="submit"], input[type="submit"]');
        if (!btn && form.id) {
            btn = document.querySelector('[type="submit"][form="' + form.id + '"]');
        }
        return btn;
    }

    // ==========================================
    // FORMULAIRES (navigation complète)
    // ==========================================
    function onSubmit(e) {
        var form = e.target;
        if (!form || form.tagName !== 'FORM') return;

        // Formulaire déjà géré en AJAX / déjà validé par un script de la page.
        if (e.defaultPrevented) return;
        if (form.dataset.noLoading !== undefined) return;
        if (form.closest('.al-modal-panel')) return; // modales AJAX (app.js)

        var target = form.getAttribute('target');
        if (target && target !== '_self') return;

        var btn = findSubmitButton(form);
        if (btn) setButtonLoading(btn);

        showLoading(form.dataset.loadingText);
    }

    // ==========================================
    // LIENS (navigation complète)
    // ==========================================
    function isSamePageAnchor(href) {
        try {
            var url = new URL(href, window.location.href);
            return !!url.hash &&
                url.origin === window.location.origin &&
                url.pathname === window.location.pathname &&
                url.search === window.location.search;
        } catch (err) {
            return false;
        }
    }

    function onClick(e) {
        if (e.defaultPrevented) return;
        if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;

        var el = e.target;
        if (!el || !el.closest) return;

        var link = el.closest('a[href]');
        if (!link) return;

        if (link.dataset.noLoading !== undefined || link.closest('[data-no-loading]')) return;
        if (link.hasAttribute('data-modal-open') || link.hasAttribute('data-modal-close')) return;
        if (link.hasAttribute('download')) return;

        var target = link.getAttribute('target');
        if (target && target !== '_self') return; // nouvel onglet : ne pas bloquer

        var href = (link.getAttribute('href') || '').trim();
        if (!href || href.charAt(0) === '#' || /^javascript:/i.test(href)) return;
        if (/^(mailto:|tel:|sms:|callto:|whatsapp:|blob:|data:)/i.test(href)) return;
        if (isSamePageAnchor(href)) return;

        showLoading(link.dataset.loadingText);
        timer = setTimeout(hideLoading, NAV_SAFETY_MS);
    }

    // ==========================================
    // INIT
    // ==========================================
    function init() {
        buildOverlay();

        // Enregistrés en dernier : tout script de page ayant déjà annulé
        // l'évènement (preventDefault) garde la main sur son propre loader.
        document.addEventListener('submit', onSubmit, false);
        document.addEventListener('click', onClick, false);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Restauration (retour navigateur / bfcache)
    window.addEventListener('pagehide', hideLoading);
    window.addEventListener('pageshow', function (e) {
        if (e.persisted) hideLoading();
    });

    // API publique
    window.AutoLink.showLoading = showLoading;
    window.AutoLink.hideLoading = hideLoading;
    window.AutoLink.setButtonLoading = setButtonLoading;
})();

