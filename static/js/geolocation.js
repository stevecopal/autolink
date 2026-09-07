/**
 * Geolocation - Récupère la position GPS pour l'enregistrement du garage.
 * Utilise l'API de géolocalisation du navigateur avec haute précision.
 */
(function() {
    'use strict';

    var locationBtn = document.getElementById('get-location-btn');
    var latInput = document.getElementById('id_latitude');
    var lngInput = document.getElementById('id_longitude');
    var accuracyInput = document.getElementById('id_gps_accuracy');
    var locationStatus = document.getElementById('location-status');
    var locationConfirm = document.getElementById('location-confirm');
    var locationMap = document.getElementById('location-map');
    var locationInfo = document.getElementById('location-info');

    if (!locationBtn) return;

    locationBtn.addEventListener('click', function() {
        if (!navigator.geolocation) {
            if (locationStatus) {
                locationStatus.textContent = 'La géolocalisation n\'est pas prise en charge par votre navigateur.';
                locationStatus.className = 'text-sm text-red-600';
            }
            return;
        }

        locationBtn.disabled = true;
        locationBtn.innerHTML = '<svg class="animate-spin h-5 w-5 mr-2 inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Localisation en cours\u2026';

        navigator.geolocation.getCurrentPosition(
            function(pos) {
                var lat = pos.coords.latitude;
                var lng = pos.coords.longitude;
                var accuracy = pos.coords.accuracy;

                if (latInput) latInput.value = lat;
                if (lngInput) lngInput.value = lng;
                if (accuracyInput) accuracyInput.value = accuracy;

                if (locationStatus) {
                    locationStatus.innerHTML = '<span class="text-green-600">&#10003; Position détectée</span>';
                }

                if (locationInfo) {
                    locationInfo.innerHTML =
                        '<div class="bg-green-50 border border-green-200 rounded-lg p-4 mt-4">' +
                        '<h4 class="font-bold text-green-800 mb-2">Position détectée</h4>' +
                        '<p class="text-sm text-green-700">Latitude : ' + lat.toFixed(6) + '</p>' +
                        '<p class="text-sm text-green-700">Longitude : ' + lng.toFixed(6) + '</p>' +
                        '<p class="text-sm text-green-700">Précision estimée : ' + Math.round(accuracy) + ' mètres</p>' +
                        '</div>';
                }

                if (locationMap) {
                    locationMap.innerHTML =
                        '<iframe width="100%" height="250" frameborder="0" style="border:0; border-radius: 0.5rem;" ' +
                        'src="https://www.openstreetmap.org/export/embed.html?bbox=' +
                        (lng - 0.01) + ',' + (lat - 0.01) + ',' +
                        (lng + 0.01) + ',' + (lat + 0.01) +
                        '&layer=mapnik&marker=' + lat + ',' + lng + '" ' +
                        'allowfullscreen></iframe>';
                    locationMap.style.display = 'block';
                }

                if (locationConfirm) {
                    locationConfirm.style.display = 'block';
                }

                locationBtn.innerHTML = '&#10003; Position enregistrée';
                locationBtn.disabled = false;
                locationBtn.classList.remove('btn-primary');
                locationBtn.classList.add('bg-green-600', 'text-white');
            },
            function(err) {
                var msg = 'Impossible d\'obtenir votre position.';
                if (err.code === 1) {
                    msg = 'Accès à la position refusé. Veuillez autoriser la géolocalisation dans les paramètres de votre navigateur.';
                } else if (err.code === 2) {
                    msg = 'Position indisponible. Veuillez vérifier que le GPS est activé.';
                } else if (err.code === 3) {
                    msg = 'La demande de position a expiré. Veuillez réessayer.';
                }
                if (locationStatus) {
                    locationStatus.textContent = msg;
                    locationStatus.className = 'text-sm text-red-600';
                }
                locationBtn.innerHTML = 'Réessayer';
                locationBtn.disabled = false;
            },
            { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
        );
    });
})();
