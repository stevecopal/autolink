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
     * Show a styled delete confirmation modal.
     * @param {string} message - Confirmation message
     * @param {Function} onConfirm - Callback when user confirms
     */
    Admin.confirmDelete = function (message, onConfirm) {
        var modal = document.getElementById('modal-delete-confirm');
        var msgEl = document.getElementById('delete-confirm-message');
        var confirmBtn = document.getElementById('delete-confirm-btn');
        if (!modal || !msgEl || !confirmBtn) return;

        msgEl.textContent = message;

        // Remove previous listener by replacing the button
        var newBtn = confirmBtn.cloneNode(true);
        confirmBtn.parentNode.replaceChild(newBtn, confirmBtn);

        newBtn.addEventListener('click', function () {
            window.AutoLink.closeModal('modal-delete-confirm');
            onConfirm();
        });

        window.AutoLink.openModal('modal-delete-confirm');
    };

})();
