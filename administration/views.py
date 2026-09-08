from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Sum, Q, Avg
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.urls import reverse

from accounts.models import User
from garages.models import Garage
from catalog.models import Part
from orders.models import Order, OrderItem
from payments.models import Payment, Refund
from reviews.models import Review
from support.models import Ticket
from core.models import City, Neighborhood
from notifications.models import Notification


def is_admin(user):
    return user.is_authenticated and user.role == 'ADMIN'


# ======================================================================
# Dashboard (refondu - sections 45/46)
# ======================================================================

@user_passes_test(is_admin)
def admin_dashboard_view(request):
    """Admin dashboard - global overview, non-duplicative with sidebar."""
    from django.db.models.functions import TruncDate

    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    # KPIs
    total_users = User.objects.count()
    total_garages = Garage.objects.count()
    verified_garages = Garage.objects.filter(verification_status='APPROVED').count()
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

    # Geographic distribution
    city_distribution = (
        Garage.objects
        .values('city__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:8]
    )
    garage_cities = City.objects.annotate(
        garage_count=Count('garages', filter=Q(garages__verification_status='APPROVED'))
    ).order_by('-garage_count')[:8]

    # Platform health indicators
    recent_payments = Payment.objects.filter(
        status='SUCCESS',
        created_at__gte=seven_days_ago
    ).count()
    recent_reviews = Review.objects.filter(
        created_at__gte=seven_days_ago,
        is_hidden=False
    ).count()
    unread_notifications = Notification.objects.filter(is_read=False).count()

    # Alert candidates
    alerts = []
    if pending_garages > 0:
        alerts.append({
            'type': 'warning',
            'title': _('Garages en attente de vérification'),
            'message': f'{pending_garages} garage{pending_garages > 1 and "s" or ""} en attente',
            'link': reverse('administration:garages') + '?status=PENDING',
        })
    if pending_tickets > 0:
        alerts.append({
            'type': 'warning',
            'title': _('Tickets ouverts'),
            'message': f'{pending_tickets} ticket{pending_tickets > 1 and "s" or ""} ouvert{pending_tickets > 1 and "s" or ""}',
            'link': reverse('administration:support'),
        })

    from django.urls import reverse

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
        'city_distribution': city_distribution,
        'garage_cities': garage_cities,
        'recent_payments': recent_payments,
        'recent_reviews': recent_reviews,
        'unread_notifications': unread_notifications,
        'alerts': alerts,
    }
    return render(request, 'dashboard/pages/admin/dashboard.html', context)


# ======================================================================
# Monitoring (section 46 - Monitoring)
# ======================================================================

@user_passes_test(is_admin)
def admin_monitoring_view(request):
    """Monitoring hub: statistiques, activite recente, alertes, vue d'ensemble."""
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    # Statistiques globales
    total_users = User.objects.count()
    total_garages = Garage.objects.count()
    total_orders = Order.objects.count()
    total_revenue = Payment.objects.filter(status='SUCCESS').aggregate(total=Sum('amount'))['total'] or 0

    # Progression 30j
    orders_30d = Order.objects.filter(created_at__gte=thirty_days_ago).count()
    users_30d = User.objects.filter(date_joined__gte=thirty_days_ago).count()
    revenue_30d = Payment.objects.filter(
        status='SUCCESS',
        created_at__gte=thirty_days_ago
    ).aggregate(total=Sum('amount'))['total'] or 0
    payments_30d = Payment.objects.filter(
        status='SUCCESS',
        created_at__gte=thirty_days_ago
    ).count()

    # Activite recente (audit-style overview via existing models)
    recent_users = User.objects.order_by('-date_joined')[:10]
    recent_orders = Order.objects.select_related('user', 'garage').order_by('-created_at')[:15]
    recent_payments = Payment.objects.select_related('order', 'user').order_by('-created_at')[:15]

    # Alertes et fonds de bilan
    pending_garages = Garage.objects.filter(verification_status='PENDING').count()
    pending_tickets = Ticket.objects.filter(status__in=['OPEN', 'IN_PROGRESS']).count()
    failed_payments_7d = Payment.objects.filter(
        status__in=['FAILED', 'PENDING'],
        created_at__gte=seven_days_ago
    ).count()
    hidden_reviews = Review.objects.filter(is_hidden=True).count()

    # Répartition géographique rapide
    garage_cities = City.objects.annotate(
        garage_count=Count('garages', filter=Q(garages__verification_status='APPROVED'))
    ).order_by('-garage_count')[:8]

    context = {
        'total_users': total_users,
        'total_garages': total_garages,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'orders_30d': orders_30d,
        'users_30d': users_30d,
        'revenue_30d': revenue_30d,
        'payments_30d': payments_30d,
        'recent_users': recent_users,
        'recent_orders': recent_orders,
        'recent_payments': recent_payments,
        'pending_garages': pending_garages,
        'pending_tickets': pending_tickets,
        'failed_payments_7d': failed_payments_7d,
        'hidden_reviews': hidden_reviews,
        'garage_cities': garage_cities,
    }
    return render(request, 'dashboard/pages/admin/monitoring/monitoring.html', context)


# ======================================================================
# Géographie (section 46)
# ======================================================================

@user_passes_test(is_admin)
def admin_geography_view(request):
    """Géographie: répartition villes/quartiers, nombre de garages par ville."""
    cities = City.objects.annotate(
        garage_count=Count('garages', filter=Q(garages__verification_status='APPROVED')),
        neighborhood_count=Count('neighborhoods'),
    ).order_by('-garage_count', 'name')

    context = {
        'cities': cities,
    }
    return render(request, 'dashboard/pages/admin/geography/geography.html', context)


# ======================================================================
# Utilisateurs
# ======================================================================

@user_passes_test(is_admin)
def admin_users_view(request):
    """Admin - manage users."""
    users = User.objects.all().order_by('-date_joined')

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
            messages.success(request, _('Statut utilisateur mis à jour.'))
        elif action == 'change_role':
            new_role = request.POST.get('role')
            if new_role in ['USER', 'CLIENT', 'ADMIN']:
                user_obj.role = new_role
                user_obj.save(update_fields=['role'])
                messages.success(request, _('Rôle utilisateur mis à jour.'))
        return redirect('administration:user_detail', user_id=user_obj.pk)

    context = {
        'user_obj': user_obj,
        'user_orders': Order.objects.filter(user=user_obj)[:10],
        'user_payments': Payment.objects.filter(user=user_obj)[:10],
    }
    return render(request, 'dashboard/pages/admin/user_detail.html', context)


# ======================================================================
# Garages
# ======================================================================

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
            Q(city__name__icontains=search)
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
    """Admin - verify/reject/suspend garage with role promotion logic."""
    from garages.services import approve_garage, reject_garage, suspend_garage
    garage = get_object_or_404(Garage.objects.select_related('owner'), pk=garage_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'verify':
            result = approve_garage(garage, admin_user=request.user)
            messages.success(request, result['message'])
        elif action == 'reject':
            reason = request.POST.get('rejection_reason', '').strip()
            result = reject_garage(garage, reason=reason, admin_user=request.user)
            messages.warning(request, result['message'])
        elif action == 'suspend':
            result = suspend_garage(garage, admin_user=request.user)
            messages.warning(request, result['message'])

        return redirect('administration:garages')

    verifications = garage.verifications.select_related('verified_by').order_by('-created_at')

    return render(request, 'dashboard/pages/admin/garages/verify.html', {
        'garage': garage,
        'verifications': verifications,
    })


# ======================================================================
# Villes
# ======================================================================

@user_passes_test(is_admin)
def admin_cities_view(request):
    """Admin - manage cities."""
    cities = City.objects.annotate(
        garage_count=Count('garages', filter=Q(garages__verification_status='APPROVED')),
        neighborhood_count=Count('neighborhoods'),
    ).order_by('name')

    search = request.GET.get('q', '')
    if search:
        cities = cities.filter(Q(name__icontains=search) | Q(slug__icontains=search))

    paginator = Paginator(cities, 20)
    page = request.GET.get('page')
    cities_page = paginator.get_page(page)

    return render(request, 'dashboard/pages/admin/cities/list.html', {
        'cities': cities_page,
        'search_query': search,
    })


@user_passes_test(is_admin)
def admin_city_edit_view(request, city_id):
    """Admin - create/edit a city via JSON-friendly form."""
    city = get_object_or_404(City, pk=city_id) if city_id else None
    is_new = city is None

    if is_new:
        city = City()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        slug = request.POST.get('slug', '').strip()
        is_active = request.POST.get('is_active') == 'on'

        errors = {}
        if not name:
            errors['name'] = _('Le nom est obligatoire.')
        if not slug:
            errors['slug'] = _('Le slug est obligatoire.')

        if errors:
            return JsonResponse({
                'success': False,
                'errors': errors,
                'form': {
                    'name': name,
                    'slug': slug,
                    'is_active': is_active,
                }
            })

        city.name = name
        city.slug = slug
        city.is_active = is_active
        city.save()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': _('Ville enregistrée.'),
                'redirect': reverse('administration:cities'),
            })

        messages.success(request, _('Ville enregistrée.'))
        return redirect('administration:cities')

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'form': {
                'name': city.name,
                'slug': city.slug,
                'is_active': city.is_active,
            },
            'initial': {
                'name': city.name,
                'slug': city.slug,
                'is_active': city.is_active,
            }
        })

    return render(request, 'dashboard/pages/admin/cities/form.html', {
        'city': city,
        'is_new': is_new,
    })


@user_passes_test(is_admin)
@require_POST
def admin_city_delete_view(request, city_id):
    """Admin - delete a city via POST (AJAX-friendly)."""
    city = get_object_or_404(City, pk=city_id)
    city_name = city.name

    garage_count = Garage.objects.filter(city=city).count()
    if garage_count > 0:
        msg = _('Impossible de supprimer cette ville : %(count)s garage(x) y est(are) associé(s).') % {'count': garage_count}
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': msg})
        messages.error(request, msg)
        return redirect('administration:cities')

    city.delete()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': _('Ville supprimée.'),
            'redirect': reverse('administration:cities'),
        })

    messages.success(request, _('Ville supprimée.'))
    return redirect('administration:cities')


# ======================================================================
# Quartiers
# ======================================================================

@user_passes_test(is_admin)
def admin_neighborhoods_view(request):
    """Admin - manage neighborhoods."""
    neighborhoods = Neighborhood.objects.select_related('city').order_by('city__name', 'name')

    search = request.GET.get('q', '')
    city_id = request.GET.get('city', '')
    if search:
        neighborhoods = neighborhoods.filter(
            Q(name__icontains=search) |
            Q(city__name__icontains=search)
        )
    if city_id:
        neighborhoods = neighborhoods.filter(city_id=city_id)

    cities = City.objects.order_by('name')

    paginator = Paginator(neighborhoods, 20)
    page = request.GET.get('page')
    neighborhoods_page = paginator.get_page(page)

    return render(request, 'dashboard/pages/admin/neighborhoods/list.html', {
        'neighborhoods': neighborhoods_page,
        'cities': cities,
        'selected_city': city_id,
        'search_query': search,
    })


@user_passes_test(is_admin)
def admin_neighborhood_edit_view(request, neighborhood_id):
    """Admin - create/edit a neighborhood via JSON-friendly form."""
    neighborhood = get_object_or_404(Neighborhood, pk=neighborhood_id) if neighborhood_id else None
    is_new = neighborhood is None

    if is_new:
        neighborhood = Neighborhood()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        slug = request.POST.get('slug', '').strip()
        city_id = request.POST.get('city', '').strip()
        is_active = request.POST.get('is_active') == 'on'

        errors = {}
        if not name:
            errors['name'] = _('Le nom est obligatoire.')
        if not slug:
            errors['slug'] = _('Le slug est obligatoire.')
        if not city_id:
            errors['city'] = _('La ville est obligatoire.')

        if errors:
            return JsonResponse({
                'success': False,
                'errors': errors,
                'form': {
                    'name': name,
                    'slug': slug,
                    'city': city_id,
                    'is_active': is_active,
                }
            })

        city = get_object_or_404(City, pk=city_id)
        neighborhood.name = name
        neighborhood.slug = slug
        neighborhood.city = city
        neighborhood.is_active = is_active
        neighborhood.save()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': _('Quartier enregistré.'),
                'redirect': reverse('administration:neighborhoods'),
            })

        messages.success(request, _('Quartier enregistré.'))
        return redirect('administration:neighborhoods')

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'form': {
                'name': neighborhood.name,
                'slug': neighborhood.slug,
                'city': str(neighborhood.city_id) if neighborhood.city_id else '',
                'is_active': neighborhood.is_active,
            },
            'initial': {
                'name': neighborhood.name,
                'slug': neighborhood.slug,
                'city': str(neighborhood.city_id) if neighborhood.city_id else '',
                'is_active': neighborhood.is_active,
            },
            'cities': [
                {'id': str(c.pk), 'name': c.name}
                for c in City.objects.order_by('name')
            ]
        })

    return render(request, 'dashboard/pages/admin/neighborhoods/form.html', {
        'neighborhood': neighborhood,
        'is_new': is_new,
        'cities': City.objects.order_by('name'),
    })


@user_passes_test(is_admin)
@require_POST
def admin_neighborhood_delete_view(request, neighborhood_id):
    """Admin - delete a neighborhood via POST (AJAX-friendly)."""
    neighborhood = get_object_or_404(Neighborhood, pk=neighborhood_id)
    name = neighborhood.name

    garage_count = Garage.objects.filter(neighborhood=neighborhood).count()
    if garage_count > 0:
        msg = _('Impossible de supprimer ce quartier : %(count)s garage(x) y est(are) associé(s).') % {'count': garage_count}
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': msg})
        messages.error(request, msg)
        return redirect('administration:neighborhoods')

    neighborhood.delete()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': _('Quartier supprimé.'),
            'redirect': reverse('administration:neighborhoods'),
        })

    messages.success(request, _('Quartier supprimé.'))
    return redirect('administration:neighborhoods')


# ======================================================================
# Commandes
# ======================================================================

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


# ======================================================================
# Paiements
# ======================================================================

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


# ======================================================================
# Support
# ======================================================================

@user_passes_test(is_admin)
def admin_support_view(request):
    """Admin - manage support tickets."""
    tickets = Ticket.objects.all().select_related('user', 'assigned_to', 'order', 'garage', 'part').order_by('-created_at')

    status = request.GET.get('status', '')
    category = request.GET.get('category', '')
    search = request.GET.get('q', '').strip()

    if status:
        tickets = tickets.filter(status=status)
    if category:
        tickets = tickets.filter(category=category)
    if search:
        tickets = tickets.filter(
            Q(ticket_number__icontains=search) |
            Q(subject__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(description__icontains=search)
        )

    paginator = Paginator(tickets, 20)
    page = request.GET.get('page')
    tickets_page = paginator.get_page(page)

    return render(request, 'dashboard/pages/admin/support/tickets/list.html', {
        'tickets': tickets_page,
        'selected_status': status,
        'selected_category': category,
        'search_query': search,
    })


@user_passes_test(is_admin)
def admin_ticket_detail_view(request, ticket_id):
    """Admin - view/assign/reply to ticket."""
    from support.models import TicketMessage
    ticket = get_object_or_404(
        Ticket.objects.select_related('user', 'order', 'garage', 'part', 'assigned_to'),
        pk=ticket_id
    )
    ticket_messages = ticket.messages.select_related('sender').order_by('created_at')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'assign':
            ticket.assigned_to = request.user
            ticket.status = Ticket.Status.IN_PROGRESS
            ticket.save(update_fields=['assigned_to', 'status', 'updated_at'])
            messages.success(request, _('Ticket pris en charge.'))

        elif action == 'resolve':
            ticket.status = Ticket.Status.RESOLVED
            ticket.resolved_at = timezone.now()
            ticket.save(update_fields=['status', 'resolved_at', 'updated_at'])
            messages.success(request, _('Ticket résolu.'))

        elif action == 'close':
            ticket.status = Ticket.Status.CLOSED
            ticket.save(update_fields=['status', 'updated_at'])
            messages.success(request, _('Ticket fermé.'))

        elif action == 'waiting':
            ticket.status = Ticket.Status.WAITING_CLIENT
            ticket.save(update_fields=['status', 'updated_at'])
            messages.success(request, _('Statut mis à jour : en attente du client.'))

        elif action == 'reply':
            content = request.POST.get('content', '').strip()
            if content:
                TicketMessage.objects.create(
                    ticket=ticket,
                    sender=request.user,
                    message=content,
                    is_internal=False,
                )
                ticket.save(update_fields=['updated_at'])
                messages.success(request, _('Réponse envoyée.'))

        return redirect('administration:ticket_detail', ticket_id=ticket.pk)

    return render(request, 'dashboard/pages/admin/support/tickets/detail.html', {
        'ticket': ticket,
        'ticket_messages': ticket_messages,
    })


# ======================================================================
# Annonces / Notifications (Communication)
# ======================================================================

@user_passes_test(is_admin)
def admin_announcements_view(request):
    """Admin - manage platform announcements."""
    announcements = (
        Notification.objects
        .filter(category='SYSTEM')
        .select_related('user')
        .order_by('-created_at')
    )

    search = request.GET.get('q', '')
    if search:
        announcements = announcements.filter(
            Q(title__icontains=search) | Q(message__icontains=search)
        )

    paginator = Paginator(announcements, 20)
    page = request.GET.get('page')
    announcements_page = paginator.get_page(page)

    return render(request, 'dashboard/pages/admin/announcements/list.html', {
        'announcements': announcements_page,
        'search_query': search,
    })


@user_passes_test(is_admin)
def admin_announcement_edit_view(request, announcement_id):
    """Admin - create/edit a system announcement."""
    announcement = get_object_or_404(Notification, pk=announcement_id) if announcement_id else None
    is_new = announcement is None

    if is_new:
        announcement = Notification(category='SYSTEM')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        message = request.POST.get('message', '').strip()
        link = request.POST.get('link', '').strip()
        is_active = request.POST.get('is_active') == 'on'

        errors = {}
        if not title:
            errors['title'] = _('Le titre est obligatoire.')
        if not message:
            errors['message'] = _('Le message est obligatoire.')

        if errors:
            return JsonResponse({
                'success': False,
                'errors': errors,
                'form': {
                    'title': title,
                    'message': message,
                    'link': link,
                    'is_active': is_active,
                }
            })

        announcement.title = title
        announcement.message = message
        announcement.link = link
        announcement.category = 'SYSTEM'
        announcement.is_read = False
        announcement.save()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': _('Annonce enregistrée.'),
                'redirect': reverse('administration:announcements'),
            })

        messages.success(request, _('Annonce enregistrée.'))
        return redirect('administration:announcements')

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'form': {
                'title': announcement.title,
                'message': announcement.message,
                'link': announcement.link,
                'is_active': not announcement.is_read or announcement.pk is None,
            },
            'initial': {
                'title': announcement.title,
                'message': announcement.message,
                'link': announcement.link,
                'is_active': not announcement.is_read or announcement.pk is None,
            }
        })

    return render(request, 'dashboard/pages/admin/announcements/form.html', {
        'announcement': announcement,
        'is_new': is_new,
    })


@user_passes_test(is_admin)
@require_POST
def admin_announcement_delete_view(request, announcement_id):
    """Admin - delete a system announcement via POST (AJAX-friendly)."""
    announcement = get_object_or_404(Notification, pk=announcement_id)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        announcement.delete()
        return JsonResponse({
            'success': True,
            'message': _('Annonce supprimée.'),
            'redirect': reverse('administration:announcements'),
        })

    announcement.delete()
    messages.success(request, _('Annonce supprimée.'))
    return redirect('administration:announcements')


# ======================================================================
# Notifications admin (gestion des notifications utilisateurs)
# ======================================================================

@user_passes_test(is_admin)
def admin_notifications_admin_view(request):
    """Admin - view/manage user notifications."""
    notifications_qs = Notification.objects.select_related('user').order_by('-created_at')

    category = request.GET.get('category', '')
    user_search = request.GET.get('q', '')
    is_read = request.GET.get('read', '')

    if category:
        notifications_qs = notifications_qs.filter(category=category)
    if user_search:
        notifications_qs = notifications_qs.filter(
            Q(user__username__icontains=user_search) |
            Q(title__icontains=user_search) |
            Q(message__icontains=user_search)
        )
    if is_read == 'unread':
        notifications_qs = notifications_qs.filter(is_read=False)
    elif is_read == 'read':
        notifications_qs = notifications_qs.filter(is_read=True)

    paginator = Paginator(notifications_qs, 20)
    page = request.GET.get('page')
    notifications_page = paginator.get_page(page)

    return render(request, 'dashboard/pages/admin/notifications_admin/list.html', {
        'notifications': notifications_page,
        'selected_category': category,
        'selected_read': is_read,
        'search_query': user_search,
    })


# ======================================================================
# Avis
# ======================================================================

@user_passes_test(is_admin)
def admin_reviews_view(request):
    """Admin - view all reviews."""
    reviews = Review.objects.all().select_related('user', 'garage', 'part').order_by('-created_at')

    paginator = Paginator(reviews, 20)
    page = request.GET.get('page')
    reviews_page = paginator.get_page(page)

    return render(request, 'dashboard/pages/admin/reviews/list.html', {'reviews': reviews_page})
