/**
 * Payment - Provider selection toggle
 */
(function() {
    'use strict';

    var radios = document.querySelectorAll('input[name="provider"]');
    var phoneField = document.getElementById('phone-field');

    if (!radios.length || !phoneField) return;

    radios.forEach(function(radio) {
        radio.addEventListener('change', function() {
            phoneField.style.display = this.value === 'CASH' ? 'none' : 'block';
        });
    });
})();
