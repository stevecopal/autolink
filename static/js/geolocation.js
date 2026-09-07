/**
 * Geolocation - Get user position for assistance requests
 */
(function() {
    'use strict';

    var locationBtn = document.getElementById('get-location-btn');
    var latInput = document.getElementById('lat');
    var lngInput = document.getElementById('lng');
    var locationStatus = document.getElementById('location-status');

    if (!locationBtn) return;

    locationBtn.addEventListener('click', function() {
        if (!navigator.geolocation) {
            if (locationStatus) {
                locationStatus.textContent = 'La géolocalisation n\'est pas prise en charge par votre navigateur.';
            }
            return;
        }

        locationBtn.disabled = true;
        locationBtn.textContent = 'Localisation…';

        navigator.geolocation.getCurrentPosition(
            function(pos) {
                if (latInput) latInput.value = pos.coords.latitude;
                if (lngInput) lngInput.value = pos.coords.longitude;
                if (locationStatus) {
                    locationStatus.textContent = 'Position enregistrée avec succès.';
                    locationStatus.className = 'text-sm text-green-600';
                }
                locationBtn.textContent = 'Position enregistrée ✓';
                locationBtn.disabled = false;
            },
            function(err) {
                var msg = 'Impossible d\'obtenir votre position.';
                if (err.code === 1) {
                    msg = 'Accès à la position refusé. Veuillez saisir votre adresse manuellement.';
                } else if (err.code === 2) {
                    msg = 'Position indisponible. Veuillez saisir votre adresse manuellement.';
                } else if (err.code === 3) {
                    msg = 'La demande de position a expiré. Veuillez réessayer.';
                }
                if (locationStatus) {
                    locationStatus.textContent = msg;
                    locationStatus.className = 'text-sm text-red-600';
                }
                locationBtn.textContent = 'Réessayer';
                locationBtn.disabled = false;
            },
            { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 }
        );
    });
})();
