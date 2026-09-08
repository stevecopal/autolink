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
        var formEl = document.getElementById('city-form-body') ||
                     document.getElementById('neighborhood-form-body') ||
                     document.getElementById('announcement-form-body');
        if (!formEl) return;

        var input = formEl.querySelector('input[name="' + inputName + '"], select[name="' + inputName + '"], textarea[name="' + inputName + '"]');
        var errorEl = input ? input.closest('.mb-4, .mb-3').querySelector('.form-error') : null;

        if (!errorEl) {
            // fallback: create error paragraph near the input
            if (input) {
                var wrapper = input.closest('.mb-4, .mb-3, .mb-2') || input.parentElement;
                var p = document.createElement('p');
                p.className = 'form-error';
                p.textContent = message;
                wrapper.appendChild(p);
            }
            return;
        }

        errorEl.textContent = message;
        if (input) input.classList.add('border-error-500');
    };

    /**
     * Clear previous field errors in a modal form.
     */
    Admin.clearFieldErrors = function () {
        var formEl = document.getElementById('city-form-body') ||
                     document.getElementById('neighborhood-form-body') ||
                     document.getElementById('announcement-form-body');
        if (!formEl) return;
        var errors = formEl.querySelectorAll('.form-error');
        errors.forEach(function (el) { el.textContent = ''; });
        var inputs = formEl.querySelectorAll('.border-error-500');
        inputs.forEach(function (el) { el.classList.remove('border-error-500'); });
    };

    /**
     * Submit a modal form via AJAX and handle success/error toasts.
     * Expects a form with data-async="true" or just any form inside a modal.
     */
    Admin.submitModalForm = function (form) {
        Admin.clearFieldErrors();

        var submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
        var originalText = '';
        var originalDisabled = false;
        if (submitBtn) {
            originalText = submitBtn.innerHTML;
            originalDisabled = submitBtn.disabled;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="al-spinner"></span> Enregistrement…';
        }

        var action = form.action;
        var method = form.method || 'POST';

        var body = new FormData(form);

        return fetch(action, {
            method: method,
            headers: {
                'X-CSRFToken': window.AutoLink.getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: body
        }).then(function (response) {
            return response.json().then(function (data) {
                return { data: data, ok: response.ok };
            }).catch(function () {
                return response.text().then(function (text) {
                    return {
                        data: { html: text, redirect: response.url !== window.location.href },
                        ok: response.ok
                    };
                });
            });
        }).then(function (result) {
            var data = result.data || {};

            if (!result.ok && data.message) {
                window.AutoLink.showToast(data.message, 'error');
                if (data.errors) {
                    Object.keys(data.errors).forEach(function (key) {
                        Admin.showFieldError(key, data.errors[key]);
                    });
                }
                return Promise.reject(data.message || 'Erreur');
            }

            if (data.success === false) {
                window.AutoLink.showToast(data.message || 'Impossible d\'enregistrer.', 'error');
                if (data.errors) {
                    Object.keys(data.errors).forEach(function (key) {
                        Admin.showFieldError(key, data.errors[key]);
                    });
                }
                return Promise.reject(data.message || 'Erreur');
            }

            // Success path
            if (data.message) {
                var type = 'success';
                if (data.type) type = data.type;
                window.AutoLink.showToast(data.message, type);
            }

            if (data.redirect) {
                if (submitBtn) {
                    submitBtn.disabled = originalDisabled;
                    submitBtn.innerHTML = originalText;
                }
                window.location.href = data.redirect;
            } else {
                if (submitBtn) {
                    submitBtn.disabled = originalDisabled;
                    submitBtn.innerHTML = originalText;
                }
                // Close modal and reset form on success
                var modal = form.closest('.al-modal-panel');
                var modalId = modal ? modal.id : null;
                if (modalId) {
                    window.AutoLink.closeModal(modalId);
                } else {
                    form.reset();
                }
            }
        }).catch(function (error) {
            window.AutoLink.showToast('Une erreur est survenue. Réessayez.', 'error');
            if (submitBtn) {
                submitBtn.disabled = originalDisabled;
                submitBtn.innerHTML = originalText;
            }
        });
    };

    /**
     * Bind modal forms to async submit behavior.
     */
    Admin.bindModalForms = function () {
        var forms = document.querySelectorAll('.al-modal-panel form[data-async="true"]');
        forms.forEach(function (form) {
            form.addEventListener('submit', function (e) {
                e.preventDefault();
                Admin.submitModalForm(form);
            });
        });
    };

    document.addEventListener('DOMContentLoaded', function () {
        Admin.bindModalForms();
    });

})();
