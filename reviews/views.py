from django.shortcuts import render
from django.core.paginator import Paginator

from accounts.decorators import admin_required, client_required
from .models import Review
from .services import ReviewService


def review_list_view(request):
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
    reviews = ReviewService.get_owner_reviews(request.user)
    paginator = Paginator(reviews, 20)
    page = request.GET.get('page')
    reviews_page = paginator.get_page(page)
    return render(request, 'dashboard/pages/client/reviews/list.html', {
        'reviews': reviews_page,
    })


@admin_required
def admin_reviews_view(request):
    reviews = ReviewService.get_all_reviews()
    paginator = Paginator(reviews, 20)
    page = request.GET.get('page')
    reviews_page = paginator.get_page(page)
    return render(request, 'dashboard/pages/admin/reviews/list.html', {
        'reviews': reviews_page,
    })
