from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.exceptions import PermissionDenied, ValidationError
from decimal import Decimal

from .models import Review, Favorite
from .forms import ReviewCreateForm
from .services import ReviewService
from orders.models import Order, OrderItem
from garages.models import Garage
from catalog.models import Part, Category
from core.models import City, Neighborhood

User = get_user_model()


class BaseReviewTest(TestCase):
    """Shared fixtures for review tests."""

    def setUp(self):
        self.client = Client()
        self.city = City.objects.create(name='Douala')
        self.neighborhood = Neighborhood.objects.create(
            name='Akwa', city=self.city,
        )

        self.buyer = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            password='testpass123',
            first_name='Buyer',
            last_name='Test',
        )
        self.other_user = User.objects.create_user(
            username='other',
            email='other@test.com',
            password='testpass123',
            first_name='Other',
            last_name='User',
        )
        self.garage_owner = User.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='testpass123',
            first_name='Owner',
            last_name='Test',
            role='CLIENT',
        )
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            role='ADMIN',
        )

        self.garage = Garage.objects.create(
            owner=self.garage_owner,
            name='Garage Test',
            slug='garage-test',
            city=self.city,
            neighborhood=self.neighborhood,
            phone='+237600000003',
            approval_status=Garage.VerificationStatus.APPROVED,
        )

        self.category = Category.objects.create(name='Moteur', slug='moteur')
        self.part = Part.objects.create(
            name='Filtre a huile',
            slug='filtre-huile',
            category=self.category,
            garage=self.garage,
            seller=self.garage_owner,
            price=Decimal('15000'),
            stock=10,
            stock_status='IN_STOCK',
            condition=Part.Condition.NEW,
            is_active=True,
        )

    def _create_order(self, user=None, garage=None, status='COMPLETED'):
        """Helper to create an order."""
        order = Order.objects.create(
            user=user or self.buyer,
            garage=garage or self.garage,
            status=status,
            subtotal=Decimal('15000'),
            total=Decimal('15000'),
        )
        OrderItem.objects.create(
            order=order,
            part=self.part,
            part_name=self.part.name,
            part_price=self.part.price,
            quantity=1,
        )
        return order


# ======================================================================
# Service tests
# ======================================================================


class ReviewServiceCanUserReviewTest(BaseReviewTest):
    """Tests for ReviewService.can_user_review_order."""

    def test_completed_order_allows_review(self):
        order = self._create_order(status='COMPLETED')
        self.assertTrue(ReviewService.can_user_review_order(self.buyer, order))

    def test_pending_order_denies_review(self):
        order = self._create_order(status='PENDING')
        self.assertFalse(ReviewService.can_user_review_order(self.buyer, order))

    def test_confirmed_order_denies_review(self):
        order = self._create_order(status='CONFIRMED')
        self.assertFalse(ReviewService.can_user_review_order(self.buyer, order))

    def test_delivered_order_denies_review(self):
        order = self._create_order(status='DELIVERED')
        self.assertFalse(ReviewService.can_user_review_order(self.buyer, order))

    def test_received_order_denies_review(self):
        order = self._create_order(status='RECEIVED')
        self.assertFalse(ReviewService.can_user_review_order(self.buyer, order))

    def test_cancelled_order_denies_review(self):
        order = self._create_order(status='CANCELLED')
        self.assertFalse(ReviewService.can_user_review_order(self.buyer, order))

    def test_no_order_denies_review(self):
        self.assertFalse(ReviewService.can_user_review_order(self.buyer, None))

    def test_unauthenticated_user_denied(self):
        from django.contrib.auth.models import AnonymousUser
        order = self._create_order()
        self.assertFalse(ReviewService.can_user_review_order(AnonymousUser(), order))

    def test_other_users_order_denied(self):
        order = self._create_order(user=self.other_user)
        self.assertFalse(ReviewService.can_user_review_order(self.buyer, order))

    def test_order_without_garage_denied(self):
        order = Order.objects.create(
            user=self.buyer,
            garage=None,
            status='COMPLETED',
            subtotal=Decimal('15000'),
            total=Decimal('15000'),
        )
        self.assertFalse(ReviewService.can_user_review_order(self.buyer, order))


class ReviewServiceCreateReviewTest(BaseReviewTest):
    """Tests for ReviewService.create_review."""

    def test_create_review_success(self):
        order = self._create_order()
        review = ReviewService.create_review(
            user=self.buyer,
            order=order,
            rating=5,
            comment='Excellent service, tres professionnel.',
            title='Super garage',
        )
        self.assertIsNotNone(review.pk)
        self.assertEqual(review.user, self.buyer)
        self.assertEqual(review.garage, self.garage)
        self.assertEqual(review.order, order)
        self.assertEqual(review.rating, 5)
        self.assertTrue(review.is_verified)
        self.assertEqual(review.review_type, Review.ReviewType.GARAGE)

    def test_create_review_denied_no_completed_order(self):
        order = self._create_order(status='PENDING')
        with self.assertRaises(PermissionDenied):
            ReviewService.create_review(
                user=self.buyer,
                order=order,
                rating=5,
                comment='Tres bon service.',
            )

    def test_create_review_denied_no_order(self):
        with self.assertRaises(PermissionDenied):
            ReviewService.create_review(
                user=self.buyer,
                order=None,
                rating=5,
                comment='Tres bon service.',
            )

    def test_create_review_denied_other_users_order(self):
        order = self._create_order(user=self.other_user)
        with self.assertRaises(PermissionDenied):
            ReviewService.create_review(
                user=self.buyer,
                order=order,
                rating=5,
                comment='Tres bon service.',
            )

    def test_create_review_duplicate_denied(self):
        order = self._create_order()
        ReviewService.create_review(
            user=self.buyer,
            order=order,
            rating=4,
            comment='Bon service, je recommande.',
        )
        with self.assertRaises(ValidationError):
            ReviewService.create_review(
                user=self.buyer,
                order=order,
                rating=5,
                comment='Encore mieux la deuxieme fois.',
            )

    def test_create_review_rating_too_low(self):
        order = self._create_order()
        with self.assertRaises(ValidationError):
            ReviewService.create_review(
                user=self.buyer,
                order=order,
                rating=0,
                comment='Service correct.',
            )

    def test_create_review_rating_too_high(self):
        order = self._create_order()
        with self.assertRaises(ValidationError):
            ReviewService.create_review(
                user=self.buyer,
                order=order,
                rating=6,
                comment='Service incroyable.',
            )

    def test_create_review_comment_too_short(self):
        order = self._create_order()
        with self.assertRaises(ValidationError):
            ReviewService.create_review(
                user=self.buyer,
                order=order,
                rating=3,
                comment='Court',
            )

    def test_create_review_updates_garage_stats(self):
        order = self._create_order()
        ReviewService.create_review(
            user=self.buyer,
            order=order,
            rating=4,
            comment='Bon travail, je recommande ce garage.',
        )
        self.garage.refresh_from_db()
        self.assertEqual(self.garage.total_reviews, 1)
        self.assertEqual(float(self.garage.trust_score), 4.0)

    def test_create_review_multiple_orders_same_garage(self):
        """User can review different orders on same garage."""
        order1 = self._create_order(status='COMPLETED')
        order2 = Order.objects.create(
            user=self.buyer,
            garage=self.garage,
            status='COMPLETED',
            subtotal=Decimal('30000'),
            total=Decimal('30000'),
        )
        OrderItem.objects.create(
            order=order2,
            part=self.part,
            part_name=self.part.name,
            part_price=self.part.price,
            quantity=2,
        )

        ReviewService.create_review(
            user=self.buyer, order=order1, rating=5,
            comment='Premiere commande, excellent service.',
        )
        ReviewService.create_review(
            user=self.buyer, order=order2, rating=4,
            comment='Deuxieme commande, toujours au top.',
        )
        self.assertEqual(Review.objects.filter(user=self.buyer, garage=self.garage).count(), 2)


class ReviewServiceHasUserReviewedTest(BaseReviewTest):
    """Tests for ReviewService.has_user_reviewed_order."""

    def test_has_not_reviewed(self):
        order = self._create_order()
        self.assertFalse(ReviewService.has_user_reviewed_order(self.buyer, order))

    def test_has_reviewed(self):
        order = self._create_order()
        Review.objects.create(
            user=self.buyer,
            review_type=Review.ReviewType.GARAGE,
            garage=self.garage,
            order=order,
            rating=5,
            comment='Excellent travail, je recommande.',
        )
        self.assertTrue(ReviewService.has_user_reviewed_order(self.buyer, order))


class ReviewServiceGetReviewsTest(BaseReviewTest):
    """Tests for review listing methods."""

    def test_get_public_reviews_excludes_hidden(self):
        order = self._create_order()
        visible = Review.objects.create(
            user=self.buyer,
            review_type=Review.ReviewType.GARAGE,
            garage=self.garage,
            order=order,
            rating=5,
            comment='Visible review for public display.',
        )
        order2 = self._create_order(user=self.other_user)
        hidden = Review.objects.create(
            user=self.other_user,
            review_type=Review.ReviewType.GARAGE,
            garage=self.garage,
            order=order2,
            rating=1,
            comment='Hidden review not shown publicly.',
            is_hidden=True,
        )
        reviews = ReviewService.get_public_reviews(self.garage)
        self.assertIn(visible, reviews)
        self.assertNotIn(hidden, reviews)

    def test_get_owner_reviews_only_shows_own_garage(self):
        other_garage = Garage.objects.create(
            owner=self.other_user,
            name='Other Garage',
            slug='other-garage',
            city=self.city,
            neighborhood=self.neighborhood,
            phone='+237600000099',
            approval_status=Garage.VerificationStatus.APPROVED,
        )
        order = self._create_order()
        Review.objects.create(
            user=self.buyer,
            review_type=Review.ReviewType.GARAGE,
            garage=self.garage,
            order=order,
            rating=5,
            comment='Review for my garage.',
        )
        order2 = Order.objects.create(
            user=self.buyer,
            garage=other_garage,
            status='COMPLETED',
            subtotal=Decimal('10000'),
            total=Decimal('10000'),
        )
        Review.objects.create(
            user=self.buyer,
            review_type=Review.ReviewType.GARAGE,
            garage=other_garage,
            order=order2,
            rating=3,
            comment='Review for other garage.',
        )
        reviews = ReviewService.get_owner_reviews(self.garage_owner)
        self.assertEqual(reviews.count(), 1)
        self.assertEqual(reviews.first().garage, self.garage)

    def test_get_all_reviews_admin(self):
        order = self._create_order()
        Review.objects.create(
            user=self.buyer,
            review_type=Review.ReviewType.GARAGE,
            garage=self.garage,
            order=order,
            rating=4,
            comment='Admin should see all reviews.',
        )
        all_reviews = ReviewService.get_all_reviews()
        self.assertEqual(all_reviews.count(), 1)


# ======================================================================
# Form tests
# ======================================================================


class ReviewCreateFormTest(TestCase):
    """Tests for ReviewCreateForm validation."""

    def test_valid_form(self):
        form = ReviewCreateForm(data={
            'rating': 4,
            'comment': 'Bon service, je recommande vivement.',
        })
        self.assertTrue(form.is_valid())

    def test_rating_zero_invalid(self):
        form = ReviewCreateForm(data={
            'rating': 0,
            'comment': 'Commentaire assez long pour etre valide.',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('rating', form.errors)

    def test_rating_six_invalid(self):
        form = ReviewCreateForm(data={
            'rating': 6,
            'comment': 'Commentaire assez long pour etre valide.',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('rating', form.errors)

    def test_comment_too_short(self):
        form = ReviewCreateForm(data={
            'rating': 3,
            'comment': 'Court',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('comment', form.errors)

    def test_comment_empty(self):
        form = ReviewCreateForm(data={
            'rating': 3,
            'comment': '',
        })
        self.assertFalse(form.is_valid())

    def test_title_optional(self):
        form = ReviewCreateForm(data={
            'rating': 5,
            'comment': 'Excellent service, tres professionnel et rapide.',
        })
        self.assertTrue(form.is_valid())


# ======================================================================
# Model constraint tests
# ======================================================================


class ReviewModelConstraintTest(BaseReviewTest):
    """Tests for model-level constraints."""

    def test_one_review_per_order_at_db_level(self):
        order = self._create_order()
        Review.objects.create(
            user=self.buyer,
            review_type=Review.ReviewType.GARAGE,
            garage=self.garage,
            order=order,
            rating=5,
            comment='First review for this order.',
        )
        with self.assertRaises(Exception):
            Review.objects.create(
                user=self.other_user,
                review_type=Review.ReviewType.GARAGE,
                garage=self.garage,
                order=order,
                rating=3,
                comment='Second review for same order should fail.',
            )

    def test_different_orders_can_be_reviewed(self):
        order1 = self._create_order()
        order2 = Order.objects.create(
            user=self.buyer,
            garage=self.garage,
            status='COMPLETED',
            subtotal=Decimal('20000'),
            total=Decimal('20000'),
        )
        Review.objects.create(
            user=self.buyer,
            review_type=Review.ReviewType.GARAGE,
            garage=self.garage,
            order=order1,
            rating=5,
            comment='First order review, very satisfied.',
        )
        Review.objects.create(
            user=self.buyer,
            review_type=Review.ReviewType.GARAGE,
            garage=self.garage,
            order=order2,
            rating=4,
            comment='Second order review, still good.',
        )
        self.assertEqual(Review.objects.filter(user=self.buyer).count(), 2)


# ======================================================================
# View tests
# ======================================================================


class ReviewCreateViewTest(BaseReviewTest):
    """Tests for the review creation view."""

    def test_review_create_requires_login(self):
        order = self._create_order()
        response = self.client.get(
            reverse('reviews:review_create') + f'?order_id={order.pk}'
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('connexion', response.url)

    def test_review_create_get_shows_form(self):
        self.client.login(email='buyer@test.com', password='testpass123')
        order = self._create_order()
        response = self.client.get(
            reverse('reviews:review_create') + f'?order_id={order.pk}'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'rating-input')

    def test_review_create_post_success(self):
        self.client.login(email='buyer@test.com', password='testpass123')
        order = self._create_order()
        response = self.client.post(
            reverse('reviews:review_create'),
            {
                'order_id': order.pk,
                'rating': 5,
                'comment': 'Excellent service, je recommande vivement ce garage.',
                'title': 'Super',
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Review.objects.count(), 1)
        review = Review.objects.first()
        self.assertEqual(review.user, self.buyer)
        self.assertEqual(review.rating, 5)
        self.assertTrue(review.is_verified)

    def test_review_create_denied_no_completed_order(self):
        self.client.login(email='buyer@test.com', password='testpass123')
        order = self._create_order(status='PENDING')
        response = self.client.get(
            reverse('reviews:review_create') + f'?order_id={order.pk}'
        )
        self.assertEqual(response.status_code, 403)

    def test_review_create_denied_other_users_order(self):
        self.client.login(email='buyer@test.com', password='testpass123')
        order = self._create_order(user=self.other_user)
        response = self.client.get(
            reverse('reviews:review_create') + f'?order_id={order.pk}'
        )
        self.assertEqual(response.status_code, 403)

    def test_review_create_no_order_id_redirects(self):
        self.client.login(email='buyer@test.com', password='testpass123')
        response = self.client.get(reverse('reviews:review_create'))
        self.assertEqual(response.status_code, 302)

    def test_review_create_duplicate_shows_warning(self):
        self.client.login(email='buyer@test.com', password='testpass123')
        order = self._create_order()
        Review.objects.create(
            user=self.buyer,
            review_type=Review.ReviewType.GARAGE,
            garage=self.garage,
            order=order,
            rating=5,
            comment='Already reviewed this order.',
        )
        response = self.client.get(
            reverse('reviews:review_create') + f'?order_id={order.pk}'
        )
        self.assertEqual(response.status_code, 302)

    def test_review_list_view(self):
        response = self.client.get(reverse('reviews:review_list'))
        self.assertEqual(response.status_code, 200)

    def test_review_list_excludes_hidden(self):
        order = self._create_order()
        Review.objects.create(
            user=self.buyer,
            review_type=Review.ReviewType.GARAGE,
            garage=self.garage,
            order=order,
            rating=5,
            comment='Visible review on public listing.',
        )
        response = self.client.get(reverse('reviews:review_list'))
        self.assertContains(response, 'Visible review on public listing.')


class GarageReviewsViewTest(BaseReviewTest):
    """Tests for the CLIENT garage reviews view."""

    def test_client_can_access(self):
        self.client.login(email='owner@test.com', password='testpass123')
        response = self.client.get(reverse('reviews:garage_reviews'))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access(self):
        self.client.login(email='admin@test.com', password='testpass123')
        response = self.client.get(reverse('reviews:garage_reviews'))
        self.assertEqual(response.status_code, 200)

    def test_regular_user_redirected(self):
        self.client.login(email='buyer@test.com', password='testpass123')
        response = self.client.get(reverse('reviews:garage_reviews'))
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_redirected(self):
        response = self.client.get(reverse('reviews:garage_reviews'))
        self.assertEqual(response.status_code, 302)


class AdminReviewsViewTest(BaseReviewTest):
    """Tests for the ADMIN reviews view."""

    def test_admin_can_access(self):
        self.client.login(email='admin@test.com', password='testpass123')
        response = self.client.get(reverse('reviews:admin_reviews'))
        self.assertEqual(response.status_code, 200)

    def test_regular_user_redirected(self):
        self.client.login(email='buyer@test.com', password='testpass123')
        response = self.client.get(reverse('reviews:admin_reviews'))
        self.assertEqual(response.status_code, 302)

    def test_garage_owner_redirected(self):
        self.client.login(email='owner@test.com', password='testpass123')
        response = self.client.get(reverse('reviews:admin_reviews'))
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_redirected(self):
        response = self.client.get(reverse('reviews:admin_reviews'))
        self.assertEqual(response.status_code, 302)

    def test_admin_sees_all_reviews(self):
        order = self._create_order()
        Review.objects.create(
            user=self.buyer,
            review_type=Review.ReviewType.GARAGE,
            garage=self.garage,
            order=order,
            rating=4,
            comment='Admin should see this review in admin view.',
        )
        self.client.login(email='admin@test.com', password='testpass123')
        response = self.client.get(reverse('reviews:admin_reviews'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin should see this review in admin view.')


# ======================================================================
# Integration: full workflow test
# ======================================================================


class ReviewWorkflowIntegrationTest(BaseReviewTest):
    """End-to-end test: user -> order -> COMPLETED -> review allowed."""

    def test_full_workflow_completed_order_allows_review(self):
        """USER -> order -> garage -> COMPLETED -> review authorized."""
        order = self._create_order(status='COMPLETED')

        self.assertTrue(ReviewService.can_user_review_order(self.buyer, order))

        review = ReviewService.create_review(
            user=self.buyer,
            order=order,
            rating=5,
            comment='Parfait, delai respecte et piece de qualite.',
        )
        self.assertIsNotNone(review.pk)
        self.assertTrue(review.is_verified)
        self.assertEqual(review.garage, self.garage)

        self.garage.refresh_from_db()
        self.assertEqual(self.garage.total_reviews, 1)
        self.assertEqual(float(self.garage.trust_score), 5.0)

    def test_workflow_no_order_denies_review(self):
        """USER -> no order -> review denied."""
        self.assertFalse(
            ReviewService.can_user_review_order(self.buyer, None)
        )

    def test_workflow_pending_order_denies_review(self):
        """USER -> order PENDING -> review denied."""
        order = self._create_order(status='PENDING')
        self.assertFalse(ReviewService.can_user_review_order(self.buyer, order))

    def test_workflow_multiple_buyers_review_same_garage(self):
        """Different buyers can review the same garage via different orders."""
        order_buyer = self._create_order(user=self.buyer, status='COMPLETED')
        order_other = Order.objects.create(
            user=self.other_user,
            garage=self.garage,
            status='COMPLETED',
            subtotal=Decimal('25000'),
            total=Decimal('25000'),
        )

        ReviewService.create_review(
            user=self.buyer, order=order_buyer, rating=5,
            comment='Premier acheteur tres satisfait du service.',
        )
        ReviewService.create_review(
            user=self.other_user, order=order_other, rating=4,
            comment='Deuxieme acheteur, bon rapport qualite prix.',
        )

        self.garage.refresh_from_db()
        self.assertEqual(self.garage.total_reviews, 2)
        expected_avg = (5 + 4) / 2
        self.assertEqual(float(self.garage.trust_score), expected_avg)

    def test_workflow_hidden_review_excluded_from_stats(self):
        """Hidden reviews should not count in garage stats."""
        order = self._create_order(status='COMPLETED')
        review = ReviewService.create_review(
            user=self.buyer, order=order, rating=1,
            comment='Review that will be hidden from stats.',
        )
        self.garage.refresh_from_db()
        self.assertEqual(self.garage.total_reviews, 1)

        review.is_hidden = True
        review.save()

        self.garage.refresh_from_db()
        self.assertEqual(self.garage.total_reviews, 0)
        self.assertEqual(float(self.garage.trust_score), 0)
