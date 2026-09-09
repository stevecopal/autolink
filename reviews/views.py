from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.translation import gettext_lazy as _

from accounts.decorators import admin_required, client_required
from orders.models import Order
from .models import Review, Favorite
from .forms import ReviewCreateForm
from .services import ReviewService


@login_required
def review_create_view(request):
    """Create a review for a completed order."""
    order_id = request.GET.get('order_id') or request.POST.get('order_id')

    if not order_id:
        messages.error(request, _('Commande non spécifiée.'))
        return redirect('reviews:review_list')

    order = get_object_or_404(Order, pk=order_id)

    if not ReviewService.can_user_review_order(request.user, order):
        raise PermissionDenied(
            _('Vous ne pouvez pas laisser un avis pour cette commande.')
        )

    if ReviewService.has_user_reviewed_order(request.user, order):
        messages.warning(request, _('Vous avez déjà laissé un avis pour cette commande.'))
        return redirect('reviews:review_list')

    if request.method == 'POST':
        form = ReviewCreateForm(request.POST)
        if form.is_valid():
            try:
                review = ReviewService.create_review(
                    user=request.user,
                    order=order,
                    rating=form.cleaned_data['rating'],
                    comment=form.cleaned_data['comment'],
                    title=form.cleaned_data.get('title', ''),
                )
                messages.success(request, _('Votre avis a été publié.'))
                return redirect('reviews:review_list')
            except (PermissionDenied, ValidationError) as e:
                messages.error(request, str(e))
    else:
        form = ReviewCreateForm()

    garage = order.garage
    return render(request, 'dashboard/pages/client/review_form.html', {
        'form': form,
        'order': order,
        'garage': garage,
    })


def review_list_view(request):
    """Public list of non-hidden reviews."""
    reviews = Review.objects.filter(
        is_hidden=False
    ).select_related('user', 'garage', 'part').order_by('-created_at')
    paginator = Paginator(reviews, 20)
    page = request.GET.get('page')
    reviews_page = paginator.get_page(page)
    return render(request, 'dashboard/pages/client/reviews/list.html', {
        'reviews': reviews_page,
    })


@client_required
def garage_reviews_view(request):
    """CLIENT view: see reviews on the user's garages."""
    reviews = ReviewService.get_owner_reviews(request.user)
    paginator = Paginator(reviews, 20)
    page = request.GET.get('page')
    reviews_page = paginator.get_page(page)
    return render(request, 'dashboard/pages/client/reviews/list.html', {
        'reviews': reviews_page,
    })


@admin_required
def admin_reviews_view(request):
    """ADMIN view: see all reviews on the platform."""
    reviews = ReviewService.get_all_reviews()
    paginator = Paginator(reviews, 20)
    page = request.GET.get('page')
    reviews_page = paginator.get_page(page)
    return render(request, 'dashboard/pages/admin/reviews/list.html', {
        'reviews': reviews_page,
    })


@login_required
def favorite_toggle_view(request):
    if request.method == 'POST':
        object_type = request.POST.get('object_type', 'GARAGE')
        object_id = request.POST.get('object_id')

        kwargs = {'user': request.user, 'object_type': object_type}
        if object_type == 'GARAGE':
            kwargs['garage_id'] = object_id
        elif object_type == 'PART':
            kwargs['part_id'] = object_id

        favorite, created = Favorite.objects.get_or_create(**kwargs)
        if not created:
            favorite.delete()
            messages.info(request, _('Removed from favorites.'))
        else:
            messages.success(request, _('Added to favorites.'))

    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def favorite_list_view(request):
    garage_favorites = request.user.favorites.filter(
        object_type='GARAGE'
    ).select_related('garage')
    part_favorites = request.user.favorites.filter(
        object_type='PART'
    ).select_related('part')
    return render(request, 'dashboard/pages/client/reviews/favorites.html', {
        'garage_favorites': garage_favorites,
        'part_favorites': part_favorites,
    })
