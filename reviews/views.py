from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Count
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator

from .models import Review, Favorite
from .forms import ReviewForm


@login_required
def review_create_view(request):
    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.review_type = request.POST.get('review_type', 'GARAGE')

            garage_id = request.POST.get('garage_id')
            part_id = request.POST.get('part_id')
            order_id = request.POST.get('order_id')

            if garage_id:
                review.garage_id = garage_id
            if part_id:
                review.part_id = part_id
            if order_id:
                review.order_id = order_id
                review.is_verified = True

            review.save()
            messages.success(request, _('Your review has been published.'))
            return redirect('reviews:review_list')
    else:
        form = ReviewForm()

    return render(request, 'dashboard/pages/client/review_form.html', {'form': form})


def review_list_view(request):
    reviews = Review.objects.filter(is_hidden=False).select_related('user', 'garage', 'part').order_by('-created_at')
    paginator = Paginator(reviews, 20)
    page = request.GET.get('page')
    reviews_page = paginator.get_page(page)
    return render(request, 'dashboard/pages/client/reviews/list.html', {'reviews': reviews_page})


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
