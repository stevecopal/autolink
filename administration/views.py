from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta

from accounts.models import User
from garages.models import Garage
from catalog.models import Part
from orders.models import Order, OrderItem
from payments.models import Payment, Refund
from reviews.models import Review
from support.models import Ticket


def is_admin(user):
    return user.is_authenticated and user.role == 'ADMIN'


@user_passes_test(is_admin)
def admin_dashboard_view(request):
    """Admin dashboard - global overview."""
    from django.db.models.functions import TruncDate
    
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    
    # Core stats
    total_users = User.objects.count()
    total_garages = Garage.objects.count()
    verified_garages = Garage.objects.filter(verification_status='VERIFIED').count()
    total_parts = Part.objects.filter(is_active=True).count()
    total_orders = Order.objects.count()
    total_payments = Payment.objects.filter(status='SUCCESS').count()
    total_revenue = Payment.objects.filter(status='SUCCESS').aggregate(total=Sum('amount'))['total'] or 0
    
    # Recent activity
    recent_orders = Order.objects.select_related('user', 'garage').order_by('-created_at')[:10]
    recent_users = User.objects.order_by('-date_joined')[:10]
    pending_tickets = Ticket.objects.filter(status__in=['OPEN', 'IN_PROGRESS']).count()
    pending_garages = Garage.objects.filter(verification_status='PENDING').count()
    
    # Time-based stats
    orders_this_month = Order.objects.filter(created_at__gte=thirty_days_ago).count()
    users_this_month = User.objects.filter(date_joined__gte=thirty_days_ago).count()
    revenue_this_month = Payment.objects.filter(
        status='SUCCESS',
        created_at__gte=thirty_days_ago
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'total_users': total_users,
        'total_garages': total_garages,
        'verified_garages': verified_garages,
        'total_parts': total_parts,
        'total_orders': total_orders,
        'total_payments': total_payments,
        'total_revenue': total_revenue,
        'recent_orders': recent_orders,
        'recent_users': recent_users,
        'pending_tickets': pending_tickets,
        'pending_garages': pending_garages,
        'orders_this_month': orders_this_month,
        'users_this_month': users_this_month,
        'revenue_this_month': revenue_this_month,
    }
    return render(request, 'dashboard/pages/admin/dashboard.html', context)


@user_passes_test(is_admin)
def admin_users_view(request):
    """Admin - manage users."""
    users = User.objects.all().order_by('-date_joined')
    
    # Filters
    role = request.GET.get('role', '')
    search = request.GET.get('q', '')
    status = request.GET.get('status', '')
    
    if role:
        users = users.filter(role=role)
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)
    
    paginator = Paginator(users, 20)
    page = request.GET.get('page')
    users_page = paginator.get_page(page)
    
    return render(request, 'dashboard/pages/admin/users/list.html', {
        'users': users_page,
        'selected_role': role,
        'search_query': search,
        'selected_status': status,
    })


@user_passes_test(is_admin)
def admin_user_detail_view(request, user_id):
    """Admin - view/edit user."""
    user_obj = get_object_or_404(User, pk=user_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'toggle_active':
            user_obj.is_active = not user_obj.is_active
            user_obj.save(update_fields=['is_active'])
            messages.success(request, _('User status updated.'))
        elif action == 'change_role':
            new_role = request.POST.get('role')
            if new_role in ['CLIENT', 'GARAGE', 'VENDEUR', 'ADMIN']:
                user_obj.role = new_role
                user_obj.save(update_fields=['role'])
                messages.success(request, _('User role updated.'))
        return redirect('administration:user_detail', user_id=user_obj.pk)
    
    context = {
        'user_obj': user_obj,
        'user_orders': Order.objects.filter(user=user_obj)[:10],
        'user_payments': Payment.objects.filter(user=user_obj)[:10],
    }
    return render(request, 'dashboard/pages/admin/user_detail.html', context)


@user_passes_test(is_admin)
def admin_garages_view(request):
    """Admin - manage garages."""
    garages = Garage.objects.all().select_related('owner').order_by('-created_at')
    
    status = request.GET.get('status', '')
    search = request.GET.get('q', '')
    
    if status:
        garages = garages.filter(verification_status=status)
    if search:
        garages = garages.filter(
            Q(name__icontains=search) |
            Q(owner__username__icontains=search) |
            Q(city__icontains=search)
        )
    
    paginator = Paginator(garages, 20)
    page = request.GET.get('page')
    garages_page = paginator.get_page(page)
    
    return render(request, 'dashboard/pages/admin/garages/list.html', {
        'garages': garages_page,
        'selected_status': status,
        'search_query': search,
    })


@user_passes_test(is_admin)
def admin_garage_verify_view(request, garage_id):
    """Admin - verify/reject garage."""
    garage = get_object_or_404(Garage, pk=garage_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'verify':
            garage.verification_status = 'VERIFIED'
            messages.success(request, _('Garage verified.'))
        elif action == 'reject':
            garage.verification_status = 'REJECTED'
            messages.info(request, _('Garage rejected.'))
        elif action == 'suspend':
            garage.verification_status = 'SUSPENDED'
            messages.warning(request, _('Garage suspended.'))
        garage.save(update_fields=['verification_status'])
        return redirect('administration:garages')
    
    return render(request, 'dashboard/pages/admin/garages/verify.html', {'garage': garage})


@user_passes_test(is_admin)
def admin_orders_view(request):
    """Admin - view all orders."""
    orders = Order.objects.all().select_related('user', 'garage').order_by('-created_at')
    
    status = request.GET.get('status', '')
    search = request.GET.get('q', '')
    
    if status:
        orders = orders.filter(status=status)
    if search:
        orders = orders.filter(
            Q(order_number__icontains=search) |
            Q(user__username__icontains=search)
        )
    
    paginator = Paginator(orders, 20)
    page = request.GET.get('page')
    orders_page = paginator.get_page(page)
    
    return render(request, 'dashboard/pages/admin/orders/list.html', {
        'orders': orders_page,
        'selected_status': status,
        'search_query': search,
    })


@user_passes_test(is_admin)
def admin_payments_view(request):
    """Admin - view all payments."""
    payments = Payment.objects.all().select_related('order', 'user').order_by('-created_at')
    
    status = request.GET.get('status', '')
    provider = request.GET.get('provider', '')
    
    if status:
        payments = payments.filter(status=status)
    if provider:
        payments = payments.filter(provider=provider)
    
    paginator = Paginator(payments, 20)
    page = request.GET.get('page')
    payments_page = paginator.get_page(page)
    
    return render(request, 'dashboard/pages/admin/payments/list.html', {
        'payments': payments_page,
        'selected_status': status,
        'selected_provider': provider,
    })


@user_passes_test(is_admin)
def admin_support_view(request):
    """Admin - manage support tickets."""
    tickets = Ticket.objects.all().select_related('user', 'assigned_to').order_by('-created_at')
    
    status = request.GET.get('status', '')
    category = request.GET.get('category', '')
    
    if status:
        tickets = tickets.filter(status=status)
    if category:
        tickets = tickets.filter(category=category)
    
    paginator = Paginator(tickets, 20)
    page = request.GET.get('page')
    tickets_page = paginator.get_page(page)
    
    return render(request, 'dashboard/pages/admin/support/tickets/list.html', {
        'tickets': tickets_page,
        'selected_status': status,
        'selected_category': category,
    })


@user_passes_test(is_admin)
def admin_ticket_detail_view(request, ticket_id):
    """Admin - view/assign ticket."""
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'assign':
            ticket.assigned_to = request.user
            ticket.status = 'IN_PROGRESS'
            ticket.save(update_fields=['assigned_to', 'status'])
            messages.success(request, _('Ticket assigned to you.'))
        elif action == 'resolve':
            ticket.status = 'RESOLVED'
            ticket.resolved_at = timezone.now()
            ticket.save(update_fields=['status', 'resolved_at'])
            messages.success(request, _('Ticket resolved.'))
        return redirect('administration:ticket_detail', ticket_id=ticket.pk)
    
    return render(request, 'dashboard/pages/admin/tickets/detail.html', {'ticket': ticket})


@user_passes_test(is_admin)
def admin_reviews_view(request):
    """Admin - view all reviews."""
    reviews = Review.objects.all().select_related('user', 'garage', 'part').order_by('-created_at')
    
    paginator = Paginator(reviews, 20)
    page = request.GET.get('page')
    reviews_page = paginator.get_page(page)
    
    return render(request, 'dashboard/pages/admin/reviews/list.html', {'reviews': reviews_page})
