/**
 * Review form - Star rating picker
 */
(function() {
    'use strict';

    var stars = document.querySelectorAll('.star-btn');
    var ratingInput = document.getElementById('rating-input');

    if (!stars.length || !ratingInput) return;

    stars.forEach(function(btn) {
        btn.addEventListener('click', function() {
            var rating = this.dataset.rating;
            ratingInput.value = rating;
            stars.forEach(function(s, i) {
                if (i < rating) {
                    s.classList.add('text-yellow-500');
                    s.classList.remove('text-gray-300');
                } else {
                    s.classList.remove('text-yellow-500');
                    s.classList.add('text-gray-300');
                }
            });
        });

        btn.addEventListener('mouseenter', function() {
            var rating = parseInt(this.dataset.rating);
            stars.forEach(function(s, i) {
                s.classList.toggle('text-yellow-500', i < rating);
                s.classList.toggle('text-gray-300', i >= rating);
            });
        });
    });

    // Reset on mouse leave
    var container = stars[0] ? stars[0].parentElement : null;
    if (container) {
        container.addEventListener('mouseleave', function() {
            var currentRating = parseInt(ratingInput.value) || 0;
            stars.forEach(function(s, i) {
                s.classList.toggle('text-yellow-500', i < currentRating);
                s.classList.toggle('text-gray-300', i >= currentRating);
            });
        });
    }
})();
