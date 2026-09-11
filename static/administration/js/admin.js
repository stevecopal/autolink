/**
 * Administration-specific JS helpers
 * Works with the existing modal system in app.js
 */

(function () {
    'use strict';

    var Admin = window.Admin || {};
    window.Admin = Admin;

    /**
     * Show a validation error next to a field inside a modal form.
     */
    Admin.showFieldError = function (inputName, message) {
        var modal = document.querySelector('.al-modal:not(.hidden) .al-modal-body');
        if (!modal) return;

        var input = modal.querySelector('input[name="' + inputName + '"], select[name="' + inputName + '"], textarea[name="' + inputName + '"]');
        if (!input) return;

        var wrapper = input.closest('.mb-4, .mb-3, .mb-2') || input.parentElement;
        var errorEl = wrapper ? wrapper.querySelector('.form-error') : null;

        if (errorEl) {
            errorEl.textContent = message;
        } else if (wrapper) {
            var p = document.createElement('p');
            p.className = 'form-error';
            p.textContent = message;
            wrapper.appendChild(p);
        }

        input.classList.add('border-error-500');
    };

    /**
     * Clear previous field errors in all modal forms.
     */
    Admin.clearFieldErrors = function () {
        document.querySelectorAll('.al-modal .form-error').forEach(function (el) {
            el.textContent = '';
        });
        document.querySelectorAll('.al-modal .border-error-500').forEach(function (el) {
            el.classList.remove('border-error-500');
        });
    };

    /**
     * Handle AJAX form responses (called by app.js form handler or directly).
     */
    Admin.handleFormResponse = function (data) {
        if (data && data.errors) {
            Object.keys(data.errors).forEach(function (key) {
                Admin.showFieldError(key, data.errors[key]);
            });
        }
    };

    /**
     * Generic confirmation modal.
     * @param {Object} opts
     *   - title        : modal heading
     *   - message      : body message (HTML allowed)
     *   - confirmLabel : text of the confirm button (default "Confirmer")
     *   - variant      : "danger" | "success" | "default" (controls icon + button color)
     *   - onConfirm    : callback invoked when the user confirms
     */
    Admin.confirm = function (opts) {
        var modal = document.getElementById('modal-delete-confirm');
        var titleEl = document.getElementById('delete-confirm-title');
        var msgEl = document.getElementById('delete-confirm-message');
        var iconWrap = document.getElementById('delete-confirm-icon');
        var confirmBtn = document.getElementById('delete-confirm-btn');
        if (!modal || !titleEl || !msgEl || !iconWrap || !confirmBtn) return;

        var variants = {
            danger: {
                wrapper: 'bg-red-100',
                icon: '<svg class="w-5 h-5 text-red-600" fill="currentColor" viewBox="0 0 20 20">' +
                        '<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>',
                btn: 'bg-red-600 hover:bg-red-700'
            },
            success: {
                wrapper: 'bg-green-100',
                icon: '<svg class="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">' +
                        '<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>',
                btn: 'bg-green-600 hover:bg-green-700'
            },
            default: {
                wrapper: 'bg-auto-100',
                icon: '<svg class="w-5 h-5 text-auto-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">' +
                        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 15m-4.5-4.5m-4.5 6m-6-4.5m-6 0m0 4.5m0-6m4.5 0"/></svg>',
                btn: 'bg-auto-orange hover:bg-auto-orange-dark'
            }
        };
        var variant = variants[opts.variant] || variants.default;

        titleEl.textContent = opts.title || '';
        msgEl.innerHTML = opts.message || '';
        iconWrap.innerHTML = variant.icon;
        confirmBtn.textContent = opts.confirmLabel || 'Confirmer';

        // Fresh listener (replaces previous button to avoid stacking callbacks).
        var newBtn = confirmBtn.cloneNode(true);
        confirmBtn.parentNode.replaceChild(newBtn, confirmBtn);

        // Reset then apply variant button classes.
        newBtn.className = 'text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors ' + variant.btn;

        newBtn.addEventListener('click', function () {
            window.AutoLink.closeModal('modal-delete-confirm');
            if (typeof opts.onConfirm === 'function') opts.onConfirm();
        });

        window.AutoLink.openModal('modal-delete-confirm');
    };

    /**
     * Styled delete confirmation (backward-compatible).
     * @param {string} message - Confirmation message
     * @param {Function} onConfirm - Callback when user confirms
     */
    Admin.confirmDelete = function (message, onConfirm) {
        Admin.confirm({
            title: 'Confirmer la suppression',
            message: message,
            confirmLabel: 'Supprimer',
            variant: 'danger',
            onConfirm: onConfirm
        });
    };

/**
     * Global confirmation interceptor.
     * Any <form> with a `data-confirm` attribute opens the styled confirmation
     * modal before submitting. Optional attributes:
     *   data-confirm-title    - modal heading
     *   data-confirm-message  - body message (HTML allowed)
     *   data-confirm-label    - confirm button text
     *   data-confirm-variant  - "danger" | "success" | "default"
     */
    document.addEventListener('submit', function (e) {
        var form = e.target;
        if (!form || form.tagName !== 'FORM') return;
        if (form.dataset.confirm === undefined) return;

        // Allow the actual submission after the user confirmed.
        if (form.dataset.confirmed === 'true') {
            form.dataset.confirmed = 'false';
            return;
        }

        e.preventDefault();

        Admin.confirm({
            title: form.dataset.confirmTitle || 'Confirmation',
            message: form.dataset.confirmMessage || 'Confirmer cette action ?',
            confirmLabel: form.dataset.confirmLabel || 'Confirmer',
            variant: form.dataset.confirmVariant || 'default',
            onConfirm: function () {
                form.dataset.confirmed = 'true';
                // requestSubmit() re-runs HTML5 validation; submit() as fallback.
                if (typeof form.requestSubmit === 'function') {
                    form.requestSubmit();
                } else {
                    form.submit();
                }
            }
        });
    });

})();
