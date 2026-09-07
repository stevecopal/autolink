/**
 * AutoLink - Recherche de mécaniciens à proximité
 * Géolocalisation GPS réelle (pas IP), carte Leaflet, liste de résultats
 */
(function () {
    'use strict';

    // ==========================================
    // Éléments DOM
    // ==========================================
    var findBtn = document.getElementById('find-nearby-btn');
    var findBtnText = document.getElementById('find-nearby-btn-text');
    var radiusSelect = document.getElementById('radius-select');
    var availableFilter = document.getElementById('available-filter');
    var searchStatus = document.getElementById('search-status');
    var resultsContainer = document.getElementById('results-container');
    var resultsList = document.getElementById('results-list');
    var resultsCount = document.getElementById('results-count');
    var resultsBadge = document.getElementById('results-badge');
    var emptyState = document.getElementById('empty-state');
    var errorState = document.getElementById('error-state');
    var errorIcon = document.getElementById('error-icon');
    var errorTitle = document.getElementById('error-title');
    var errorMessage = document.getElementById('error-message');
    var retryBtn = document.getElementById('retry-btn');

    if (!findBtn) return;

    // ==========================================
    // État
    // ==========================================
    var map = null;
    var markers = [];
    var userMarker = null;
    var markerLayer = null;
    var currentUserPosition = null;
    var isSearching = false;

    // Seuil de précision : au-delà de 1000m, c'est probablement de l'IP
    var GPS_ACCURACY_THRESHOLD_METERS = 1000;

    // ==========================================
    // Textes i18n (fallbacks français)
    // ==========================================
    var TEXTS = {
        locating: 'Recherche de votre position GPS…',
        searching: 'Recherche de mécaniciens à proximité…',
        geolocation_not_supported: 'La géolocalisation n\'est pas prise en charge par votre navigateur.',
        permission_denied: 'Nous avons besoin de votre position pour trouver les mécaniciens à proximité. Autorisez l\'accès à votre position dans les paramètres de votre navigateur.',
        position_unavailable: 'Votre position est indisponible. Vérifiez que le GPS est activé sur votre appareil.',
        timeout: 'La demande de localisation a expiré. Veuillez réessayer.',
        generic_error: 'Impossible d\'obtenir votre position. Vous pouvez essayer à nouveau ou saisir votre adresse manuellement.',
        low_accuracy: 'La précision de la position est faible (basée sur l\'IP). Activez le GPS pour un résultat plus précis.',
        retry_with_gps: 'Réessayer avec le GPS',
        no_results: 'Aucun mécanicien trouvé dans cette zone.',
        try_radius: 'Essayez d\'élargir le rayon de recherche.',
        results_found: '{count} mécanicien(s) trouvé(s)',
        available: 'Disponible',
        busy: 'Occupé',
        closed: 'Fermé',
        open_now: 'Ouvert',
        closed_now: 'Fermé',
        call: 'Appeler',
        view: 'Voir',
        km_away: '{distance}',
        you_are_here: 'Vous êtes ici',
        error_title: 'Erreur de localisation',
        manual_search: 'Ou recherchez par ville :',
        search_by_city: 'Rechercher',
    };

    function getText(key) {
        var el = document.querySelector('[data-i18n="' + key + '"]');
        if (el) return el.textContent.trim();
        return TEXTS[key] || key;
    }

    // ==========================================
    // Initialisation de la carte Leaflet
    // ==========================================
    function initMap(center) {
        if (map) {
            map.setView([center.lat, center.lng], 13);
            return;
        }

        map = L.map('nearby-map', {
            center: [center.lat, center.lng],
            zoom: 13,
            zoomControl: true,
            scrollWheelZoom: true,
        });

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            maxZoom: 19,
        }).addTo(map);

        markerLayer = L.layerGroup().addTo(map);
    }

    // ==========================================
    // Marqueurs
    // ==========================================
    function createGarageIcon(isAvailable) {
        var color = isAvailable ? '#10B981' : '#F59E0B';
        return L.divIcon({
            className: 'garage-marker',
            html: '<div style="width:32px;height:32px;background:' + color + ';border:3px solid white;border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;font-size:16px;">🔧</div>',
            iconSize: [32, 32],
            iconAnchor: [16, 16],
            popupAnchor: [0, -20],
        });
    }

    function createUserIcon() {
        return L.divIcon({
            className: 'user-marker',
            html: '<div style="width:24px;height:24px;background:#3B82F6;border:3px solid white;border-radius:50%;box-shadow:0 2px 8px rgba(59,130,246,0.5);"></div>',
            iconSize: [24, 24],
            iconAnchor: [12, 12],
        });
    }

    function addMarkers(garages, userPos) {
        if (markerLayer) markerLayer.clearLayers();
        markers = [];

        if (userPos) {
            userMarker = L.marker([userPos.lat, userPos.lng], {
                icon: createUserIcon(),
                zIndexOffset: 1000,
            }).bindPopup('<strong>' + getText('you_are_here') + '</strong>');
            userMarker.addTo(markerLayer);
        }

        garages.forEach(function (garage, index) {
            if (!garage.latitude || !garage.longitude) return;

            var marker = L.marker([garage.latitude, garage.longitude], {
                icon: createGarageIcon(garage.is_available),
            });

            var popupContent = '<div style="min-width:200px;">' +
                '<h3 style="font-weight:bold;margin:0 0 4px 0;font-size:14px;">' + escapeHtml(garage.name) + '</h3>' +
                '<p style="margin:0 0 4px 0;color:#666;font-size:12px;">📍 ' + escapeHtml(garage.distance_display) + '</p>' +
                '<p style="margin:0 0 8px 0;">' +
                (garage.is_available
                    ? '<span style="color:#10B981;font-weight:bold;font-size:12px;">● ' + getText('available') + '</span>'
                    : '<span style="color:#F59E0B;font-weight:bold;font-size:12px;">● ' + getText('busy') + '</span>') +
                '</p>' +
                '<a href="' + garage.url + '" style="display:inline-block;background:#CD8135;color:white;padding:6px 12px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:12px;">' + getText('view') + '</a>' +
                '</div>';

            marker.bindPopup(popupContent);
            marker.addTo(markerLayer);
            marker._garageIndex = index;
            markers.push(marker);
        });
    }

    function fitMapBounds(userPos, garages) {
        if (!map) return;

        var bounds = L.latLngBounds([]);

        if (userPos) {
            bounds.extend([userPos.lat, userPos.lng]);
        }

        garages.forEach(function (g) {
            if (g.latitude && g.longitude) {
                bounds.extend([g.latitude, g.longitude]);
            }
        });

        if (bounds.isValid()) {
            map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
        }
    }

    // ==========================================
    // Affichage des résultats
    // ==========================================
    function renderResults(garages) {
        resultsList.innerHTML = '';

        if (garages.length === 0) {
            resultsList.style.display = 'none';
            emptyState.classList.remove('hidden');
            resultsBadge.style.display = 'none';
            return;
        }

        emptyState.classList.add('hidden');
        resultsList.style.display = 'block';

        resultsBadge.textContent = garages.length;
        resultsBadge.style.display = 'inline-flex';

        garages.forEach(function (garage, index) {
            var card = document.createElement('div');
            card.className = 'garage-result-card bg-white rounded-xl p-4 border border-auto-100/50 shadow-card cursor-pointer hover:shadow-card-hover transition-all duration-200';
            card.setAttribute('role', 'listitem');
            card.setAttribute('data-index', index);
            card.setAttribute('tabindex', '0');
            card.setAttribute('aria-label', garage.name + ' - ' + garage.distance_display);

            var availabilityBadge = garage.is_available
                ? '<span class="badge-success text-xs">' + getText('available') + '</span>'
                : '<span class="badge-warning text-xs">' + getText('busy') + '</span>';

            var openBadge = garage.is_open_now
                ? '<span class="badge-success text-xs">' + getText('open_now') + '</span>'
                : '<span class="badge-neutral text-xs">' + getText('closed_now') + '</span>';

            card.innerHTML =
                '<div class="flex items-start gap-3">' +
                    '<div class="w-14 h-14 rounded-xl bg-auto-100 flex items-center justify-center text-2xl flex-shrink-0 overflow-hidden">' +
                        (garage.logo_url
                            ? '<img src="' + garage.logo_url + '" alt="" class="w-full h-full object-cover">'
                            : '🔧') +
                    '</div>' +
                    '<div class="flex-1 min-w-0">' +
                        '<div class="flex items-start justify-between gap-2">' +
                            '<h3 class="font-bold text-auto-dark text-sm truncate">' + escapeHtml(garage.name) + '</h3>' +
                            '<span class="text-auto-orange font-bold text-sm whitespace-nowrap">' + escapeHtml(garage.distance_display) + '</span>' +
                        '</div>' +
                        '<p class="text-auto-600 text-xs mt-1 truncate">📍 ' + escapeHtml(garage.neighborhood || garage.city || '') + '</p>' +
                        '<div class="flex items-center gap-2 mt-2">' +
                            availabilityBadge +
                            openBadge +
                            '<span class="text-auto-gold text-xs">⭐ ' + garage.trust_score + '</span>' +
                        '</div>' +
                        '<div class="flex items-center gap-2 mt-3 pt-2 border-t border-auto-100">' +
                            (garage.phone
                                ? '<a href="tel:' + escapeHtml(garage.phone) + '" class="text-auto-orange hover:text-auto-orange-dark font-bold text-xs transition flex items-center gap-1" aria-label="' + getText('call') + ' ' + escapeHtml(garage.name) + '">' +
                                    '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"></path></svg>' +
                                    '<span class="hidden sm:inline">' + getText('call') + '</span>' +
                                  '</a>'
                                : '') +
                            '<a href="' + garage.url + '" class="text-auto-dark hover:text-auto-orange font-bold text-xs transition flex items-center gap-1">' +
                                getText('view') +
                                ' <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>' +
                            '</a>' +
                        '</div>' +
                    '</div>' +
                '</div>';

            card.addEventListener('click', function () {
                focusMarker(index);
            });
            card.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    focusMarker(index);
                }
            });

            resultsList.appendChild(card);
        });
    }

    function focusMarker(index) {
        if (!markers[index] || !map) return;

        var prevActive = resultsList.querySelector('.active');
        if (prevActive) prevActive.classList.remove('active');

        var card = resultsList.querySelector('[data-index="' + index + '"]');
        if (card) {
            card.classList.add('active');
            card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }

        var marker = markers[index];
        map.setView(marker.getLatLng(), Math.max(map.getZoom(), 15));
        marker.openPopup();
    }

    // ==========================================
    // États UI
    // ==========================================
    function showLoading(message) {
        searchStatus.classList.remove('hidden');
        searchStatus.innerHTML =
            '<div class="flex items-center gap-3 text-auto-600">' +
                '<svg class="animate-spin w-5 h-5 text-auto-orange search-pulse" fill="none" viewBox="0 0 24 24">' +
                    '<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>' +
                    '<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 4.373 0 12h4z"></path>' +
                '</svg>' +
                '<span class="text-sm font-medium">' + message + '</span>' +
            '</div>';
    }

    function hideLoading() {
        searchStatus.classList.add('hidden');
    }

    function showError(title, message, showRetry) {
        resultsContainer.style.display = 'none';
        errorState.classList.remove('hidden');
        errorTitle.textContent = title;
        errorMessage.textContent = message;
        retryBtn.style.display = showRetry ? 'inline-flex' : 'none';
    }

    function hideError() {
        errorState.classList.add('hidden');
    }

    function showResults() {
        hideError();
        resultsContainer.style.display = '';
    }

    function showAccuracyWarning(accuracy) {
        // Afficher un avertissement si la précision est faible (basée sur IP)
        var warningDiv = document.getElementById('accuracy-warning');
        if (!warningDiv) {
            warningDiv = document.createElement('div');
            warningDiv.id = 'accuracy-warning';
            warningDiv.className = 'mt-3 bg-warning-50 border border-warning-500/30 rounded-lg p-3 text-sm text-warning-700 flex items-center gap-2';
            var searchControls = document.getElementById('search-controls');
            if (searchControls) {
                searchControls.appendChild(warningDiv);
            }
        }
        var accuracyMeters = Math.round(accuracy);
        warningDiv.innerHTML =
            '<svg class="w-5 h-5 flex-shrink-0 text-warning-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>' +
            '<div>' +
                '<span class="font-bold">' + getText('low_accuracy') + '</span>' +
                '<span class="block text-xs mt-0.5 opacity-75">Précision : ~' + accuracyMeters + ' m (position estimée par le réseau)</span>' +
            '</div>';
        warningDiv.style.display = 'flex';
    }

    // ==========================================
    // Géolocalisation — FORCER GPS RÉEL
    // ==========================================
    function requestGPSPosition(options) {
        return new Promise(function (resolve, reject) {
            if (!navigator.geolocation) {
                reject({ code: 0, message: getText('geolocation_not_supported') });
                return;
            }

            navigator.geolocation.getCurrentPosition(
                function (pos) {
                    resolve({
                        lat: pos.coords.latitude,
                        lng: pos.coords.longitude,
                        accuracy: pos.coords.accuracy,
                        timestamp: pos.timestamp,
                    });
                },
                function (err) {
                    reject(err);
                },
                options
            );
        });
    }

    function getUserPosition() {
        // Tentative 1 : GPS haute précision, pas de cache
        return requestGPSPosition({
            enableHighAccuracy: true,   // Forcer GPS matériel
            timeout: 15000,             // 15 secondes max
            maximumAge: 0,              // Pas de position en cache → toujours fraîche
        }).then(function (pos) {
            // Vérifier la précision
            if (pos.accuracy > GPS_ACCURACY_THRESHOLD_METERS) {
                // Position probablement basée sur IP, retry avec force
                return requestGPSPosition({
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0,
                }).catch(function () {
                    // Si le 2e échoue, accepter la 1re position avec warning
                    showAccuracyWarning(pos.accuracy);
                    return pos;
                });
            }
            return pos;
        }).catch(function (err) {
            // Tentative 2 : forcer encore une fois
            return requestGPSPosition({
                enableHighAccuracy: true,
                timeout: 20000,
                maximumAge: 0,
            }).catch(function () {
                // Tout a échoué, propager l'erreur initiale
                throw err;
            });
        });
    }

    function handleGeoError(err) {
        var title = getText('error_title');
        var message = '';
        var showRetry = true;

        if (err.code === 0) {
            message = getText('geolocation_not_supported');
            showRetry = false;
        } else if (err.code === 1) {
            message = getText('permission_denied');
            showRetry = false;
        } else if (err.code === 2) {
            message = getText('position_unavailable') + ' ' + getText('retry_with_gps');
        } else if (err.code === 3) {
            message = getText('timeout') + ' ' + getText('retry_with_gps');
        } else {
            message = err.message || getText('generic_error');
        }

        showError(title, message, showRetry);
    }

    // ==========================================
    // Recherche API
    // ==========================================
    function searchNearby(position) {
        if (isSearching) return;
        isSearching = true;

        currentUserPosition = position;
        var radius = radiusSelect.value;
        var available = availableFilter.checked ? '1' : '';

        showLoading(getText('searching'));

        var url = '/api/nearby/?lat=' + encodeURIComponent(position.lat) +
                  '&lng=' + encodeURIComponent(position.lng) +
                  '&radius=' + encodeURIComponent(radius) +
                  (available ? '&available=' + available : '');

        fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
        })
        .then(function (response) {
            if (!response.ok) {
                throw new Error('HTTP ' + response.status);
            }
            return response.json();
        })
        .then(function (data) {
            hideLoading();
            isSearching = false;

            if (!data.success) {
                showError(
                    getText('error_title'),
                    (data.errors && data.errors[0]) || getText('generic_error'),
                    true
                );
                return;
            }

            showResults();
            initMap(position);
            addMarkers(data.results, position);
            fitMapBounds(position, data.results);
            renderResults(data.results);

            resultsCount.textContent = data.total + ' résultat' + (data.total > 1 ? 's' : '');
        })
        .catch(function (error) {
            hideLoading();
            isSearching = false;
            showError(
                getText('error_title'),
                getText('generic_error'),
                true
            );
        });
    }

    // ==========================================
    // Événements
    // ==========================================
    findBtn.addEventListener('click', function () {
        if (isSearching) return;

        findBtn.disabled = true;
        findBtnText.textContent = getText('locating');

        getUserPosition()
            .then(function (pos) {
                findBtn.disabled = false;
                findBtnText.textContent = getText('searching');
                searchNearby(pos);
            })
            .catch(function (err) {
                findBtn.disabled = false;
                findBtnText.textContent = 'Trouver un mécanicien';
                handleGeoError(err);
            });
    });

    radiusSelect.addEventListener('change', function () {
        if (currentUserPosition) {
            searchNearby(currentUserPosition);
        }
    });

    availableFilter.addEventListener('change', function () {
        if (currentUserPosition) {
            searchNearby(currentUserPosition);
        }
    });

    retryBtn.addEventListener('click', function () {
        hideError();
        findBtn.click();
    });

    // ==========================================
    // Utilitaires
    // ==========================================
    function escapeHtml(str) {
        if (!str) return '';
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

})();
