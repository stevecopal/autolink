/**
 * Checkout - Delivery fields toggle
 */
(function() {
    'use strict';

    var radios = document.querySelectorAll('input[name="fulfillment"]');
    var deliveryFields = document.getElementById('delivery-fields');

    if (!radios.length || !deliveryFields) return;

    radios.forEach(function(radio) {
        radio.addEventListener('change', function() {
            deliveryFields.classList.toggle('hidden', this.value !== 'DELIVERY');
        });
    });
})();
