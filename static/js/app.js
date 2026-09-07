/**
 * AutoLink - Main Application JavaScript
 * Toasts + Modals + Navigation + Notifications
 */

(function() {
    'use strict';

    // ==========================================
    // CSRF Token Helper
    // ==========================================
    window.AutoLink = window.AutoLink || {};

    window.AutoLink.getCSRFToken = function() {
        var cookie = document.cookie.split(';').find(function(c) {
            return c.trim().startsWith('csrftoken=');
        });
        return cookie ? cookie.split('=')[1] : '';
    };

    window.AutoLink.post = function(url, data) {
        return fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.AutoLink.getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify(data),
        });
    };

    // ==========================================
    // TOAST SYSTEM - Fixed top-right, smooth
    // ==========================================
    var toastContainer = null;

    function ensureToastContainer() {
        if (toastContainer) return toastContainer;
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.setAttribute('role', 'alert');
        toastContainer.setAttribute('aria-live', 'polite');
        toastContainer.style.cssText = 'position:fixed;top:1rem;right:1rem;z-index:9999;display:flex;flex-direction:column;gap:0.5rem;max-width:24rem;width:calc(100vw - 2rem);pointer-events:none;';
        document.body.appendChild(toastContainer);
        return toastContainer;
    }

    var toastIcons = {
        success: '<svg class="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>',
        error: '<svg class="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>',
        warning: '<svg class="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>',
        info: '<svg class="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>',
    };

    var toastColors = {
        success: { bg: '#ECFDF5', border: '#6EE7B7', text: '#065F46', iconBg: '#D1FAE5' },
        error:   { bg: '#FEF2F2', border: '#FCA5A5', text: '#991B1B', iconBg: '#FEE2E2' },
        warning: { bg: '#FFFBEB', border: '#FCD34D', text: '#92400E', iconBg: '#FEF3C7' },
        info:    { bg: '#EFF6FF', border: '#93C5FD', text: '#1E40AF', iconBg: '#DBEAFE' },
    };

    window.AutoLink.showToast = function(message, type) {
        type = type || 'info';
        var c = toastColors[type] || toastColors.info;
        var icon = toastIcons[type] || toastIcons.info;
        var container = ensureToastContainer();

        var toast = document.createElement('div');
        toast.style.cssText = 'pointer-events:auto;display:flex;align-items:flex-start;gap:0.75rem;padding:1rem 1rem;border-radius:0.75rem;box-shadow:0 10px 25px -5px rgba(0,0,0,0.15),0 8px 10px -6px rgba(0,0,0,0.1);font-family:"Space Mono",monospace;font-size:0.875rem;line-height:1.5;background:' + c.bg + ';border:1px solid ' + c.border + ';color:' + c.text + ';transform:translateX(120%);opacity:0;transition:transform 0.35s cubic-bezier(0.4,0,0.2,1),opacity 0.35s cubic-bezier(0.4,0,0.2,1);';

        toast.innerHTML =
            '<div style="background:' + c.iconBg + ';border-radius:0.5rem;padding:0.375rem;flex-shrink:0;">' + icon + '</div>' +
            '<div style="flex:1;word-break:break-word;">' + message + '</div>' +
            '<button onclick="this.closest(\'[role=alert]\').remove()" style="flex-shrink:0;opacity:0.6;transition:opacity 0.2s;cursor:pointer;background:none;border:none;color:inherit;padding:0;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.6" aria-label="Close">' +
                '<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/></svg>' +
            '</button>';

        container.appendChild(toast);

        // Trigger animation
        requestAnimationFrame(function() {
            requestAnimationFrame(function() {
                toast.style.transform = 'translateX(0)';
                toast.style.opacity = '1';
            });
        });

        // Auto dismiss
        var timeout = setTimeout(function() {
            dismissToast(toast);
        }, 5000);

        toast.addEventListener('mouseenter', function() {
            clearTimeout(timeout);
        });
        toast.addEventListener('mouseleave', function() {
            timeout = setTimeout(function() {
                dismissToast(toast);
            }, 2000);
        });
    };

    function dismissToast(toast) {
        if (!toast || !toast.parentNode) return;
        toast.style.transform = 'translateX(120%)';
        toast.style.opacity = '0';
        setTimeout(function() {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, 350);
    }

    // Process Django messages on page load → convert to toasts
    var messagesContainer = document.getElementById('messages-container');
    if (messagesContainer) {
        var djangoMessages = messagesContainer.querySelectorAll('[data-toast]');
        djangoMessages.forEach(function(el) {
            var type = el.getAttribute('data-toast');
            var message = el.textContent.trim();

            // Map Django message tags to toast types
            var toastType = 'info';
            if (type === 'success') toastType = 'success';
            else if (type === 'error' || type === 'danger') toastType = 'error';
            else if (type === 'warning') toastType = 'warning';
            else if (type === 'info') toastType = 'info';

            window.AutoLink.showToast(message, toastType);
        });
        messagesContainer.remove();
    }

    // ==========================================
    // MODAL SYSTEM
    // ==========================================
    var activeModal = null;

    window.AutoLink.openModal = function(modalId) {
        var modal = document.getElementById(modalId);
        if (!modal) return;
        activeModal = modal;
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        requestAnimationFrame(function() {
            requestAnimationFrame(function() {
                modal.querySelector('.al-modal-panel').style.transform = 'scale(1) translateY(0)';
                modal.querySelector('.al-modal-panel').style.opacity = '1';
                modal.querySelector('.al-modal-backdrop').style.opacity = '1';
            });
        });
        // Focus first input
        var firstInput = modal.querySelector('input:not([type=hidden]), textarea, select');
        if (firstInput) setTimeout(function() { firstInput.focus(); }, 350);
    };

    window.AutoLink.closeModal = function(modalId) {
        var modal = document.getElementById(modalId || (activeModal && activeModal.id));
        if (!modal) return;
        modal.querySelector('.al-modal-panel').style.transform = 'scale(0.95) translateY(10px)';
        modal.querySelector('.al-modal-panel').style.opacity = '0';
        modal.querySelector('.al-modal-backdrop').style.opacity = '0';
        setTimeout(function() {
            modal.classList.add('hidden');
            document.body.style.overflow = '';
            activeModal = null;
        }, 250);
    };

    // Close modal on backdrop click
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('al-modal-backdrop')) {
            var modalId = activeModal ? activeModal.id : null;
            window.AutoLink.closeModal(modalId);
            var form = activeModal && activeModal.querySelector('form');
            if (form) form.reset();
        }
    });

    // Close modal on Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && activeModal) {
            window.AutoLink.closeModal();
            var form = activeModal && activeModal.querySelector('form');
            if (form) form.reset();
        }
    });

    // Open modal triggers
    document.addEventListener('click', function(e) {
        var trigger = e.target.closest('[data-modal-open]');
        if (trigger) {
            e.preventDefault();
            window.AutoLink.openModal(trigger.getAttribute('data-modal-open'));
        }
        var closeTrigger = e.target.closest('[data-modal-close]');
        if (closeTrigger) {
            e.preventDefault();
            window.AutoLink.closeModal();
        }
    });

    // Form submission inside modals
    document.addEventListener('submit', function(e) {
        var modal = e.target.closest('.al-modal-panel');
        if (!modal) return;
        var form = e.target.closest('form');
        if (!form) return;

        e.preventDefault();

        var submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
        var originalText = submitBtn ? submitBtn.innerHTML : '';
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<svg class="animate-spin h-4 w-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 4.373 0 12h4z"></path></svg> Envoi...';
        }

        var formData = new FormData(form);
        var csrfToken = window.AutoLink.getCSRFToken();

        fetch(form.action, {
            method: form.method,
            headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: new URLSearchParams(new FormData(form)).toString(),
        })
        .then(function(response) {
            return response.json().catch(function() {
                // Fallback for non-JSON responses (redirects, etc.)
                return response.text().then(function(text) {
                    return { html: text, redirect: response.url !== window.location.href };
                });
            });
        })
        .then(function(data) {
            if (data && data.message) {
                var msgType = data.type || 'info';
                window.AutoLink.showToast(data.message, msgType);
            }
            if (data && data.redirect) {
                window.location.href = data.redirect;
            } else {
                // Close modal on success
                var modalId = modal.id;
                window.AutoLink.closeModal(modalId);
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }
            }
        })
        .catch(function(error) {
            window.AutoLink.showToast('Une erreur est survenue. Veuillez réessayer.', 'error');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }
        });
    });

    // ==========================================
    // MOBILE NAVIGATION
    // ==========================================
    var mobileMenuBtn = document.getElementById('mobile-menu-btn');
    var mobileMenu = document.getElementById('mobile-menu');

    if (mobileMenuBtn && mobileMenu) {
        mobileMenuBtn.addEventListener('click', function() {
            mobileMenu.classList.toggle('hidden');
        });
        document.addEventListener('click', function(e) {
            if (!mobileMenuBtn.contains(e.target) && !mobileMenu.contains(e.target)) {
                mobileMenu.classList.add('hidden');
            }
        });
    }

    // ==========================================
    // NOTIFICATIONS POLLING
    // ==========================================
    var notifBadge = document.getElementById('notif-badge');

    async function checkNotifications() {
        if (!notifBadge) return;
        try {
            var res = await fetch('/notifications/api/count/');
            if (!res.ok) return;
            var data = await res.json();
            if (data.unread_count > 0) {
                notifBadge.textContent = data.unread_count > 99 ? '99+' : data.unread_count;
                notifBadge.classList.remove('hidden');
            } else {
                notifBadge.classList.add('hidden');
            }
        } catch (e) { /* silent */ }
    }

    if (notifBadge) {
        checkNotifications();
        setInterval(checkNotifications, 60000);
    }

    // ==========================================
    // GEOLOCATION HELPER
    // ==========================================
    window.AutoLink.getLocation = function() {
        return new Promise(function(resolve, reject) {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation not supported'));
                return;
            }
            navigator.geolocation.getCurrentPosition(
                function(pos) {
                    resolve({
                        latitude: pos.coords.latitude,
                        longitude: pos.coords.longitude,
                        accuracy: pos.coords.accuracy,
                    });
                },
                function(err) { reject(err); },
                { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 }
            );
        });
    };

})();
