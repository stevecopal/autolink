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
                locationStatus.textContent = 'Geolocation is not supported by your browser.';
            }
            return;
        }

        locationBtn.disabled = true;
        locationBtn.textContent = 'Locating...';

        navigator.geolocation.getCurrentPosition(
            function(pos) {
                if (latInput) latInput.value = pos.coords.latitude;
                if (lngInput) lngInput.value = pos.coords.longitude;
                if (locationStatus) {
                    locationStatus.textContent = 'Position recorded successfully.';
                    locationStatus.className = 'text-sm text-green-600';
                }
                locationBtn.textContent = 'Position recorded ✓';
                locationBtn.disabled = false;
            },
            function(err) {
                var msg = 'Unable to get your position.';
                if (err.code === 1) {
                    msg = 'Position access denied. Please enter your address manually.';
                } else if (err.code === 2) {
                    msg = 'Position unavailable. Please enter your address manually.';
                } else if (err.code === 3) {
                    msg = 'Position request timed out. Please try again.';
                }
                if (locationStatus) {
                    locationStatus.textContent = msg;
                    locationStatus.className = 'text-sm text-red-600';
                }
                locationBtn.textContent = 'Try again';
                locationBtn.disabled = false;
            },
            { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 }
        );
    });
})();
