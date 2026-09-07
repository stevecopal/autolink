/**
 * Vehicle form - Brand/Model dependent select
 */
(function() {
    'use strict';

    var brandSelect = document.getElementById('brand-select');
    var modelSelect = document.getElementById('model-select');

    if (!brandSelect || !modelSelect) return;

    brandSelect.addEventListener('change', function() {
        var brandId = this.value;
        modelSelect.innerHTML = '<option value="">Loading...</option>';

        if (!brandId) {
            modelSelect.innerHTML = '<option value="">Select a model</option>';
            return;
        }

        fetch('/vehicules/api/marques/' + brandId + '/modeles/')
            .then(function(res) { return res.json(); })
            .then(function(models) {
                modelSelect.innerHTML = '<option value="">Select a model</option>';
                models.forEach(function(m) {
                    var opt = document.createElement('option');
                    opt.value = m.id;
                    opt.textContent = m.name;
                    modelSelect.appendChild(opt);
                });
            })
            .catch(function() {
                modelSelect.innerHTML = '<option value="">Error loading models</option>';
            });
    });
})();
