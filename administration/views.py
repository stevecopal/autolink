from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from accounts.models import User
from catalog.models import Part
from core.models import City, Neighborhood
from garages.models import Garage
from payments.models import Payment, Receipt
from support.models import Ticket

from .forms import CityForm, NeighborhoodForm

def is_admin(user):
    """
    Vérifie si l'utilisateur est ADMIN ou SUPERUSER.
    """
    return user.is_authenticated and (
        user.is_superuser
        or user.is_staff
        or getattr(user, "role", None) in [user.Role.ADMIN, user.Role.SUPERUSER]
    )


@user_passes_test(is_admin)
def admin_dashboard_view(request):
    from django.db.models.functions import TruncDate

    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    total_users = User.objects.count()
    total_garages = Garage.objects.count()
    verified_garages = Garage.objects.filter(
        approval_status=Garage.ApprovalStatus.APPROVED
    ).count()
    total_parts = Part.objects.filter(is_active=True).count()
    total_payments = Payment.objects.filter(status="SUCCESS").count()
    total_revenue = (
        Payment.objects.filter(status="SUCCESS").aggregate(total=Sum("amount"))["total"]
        or 0
    )

    recent_users = User.objects.order_by("-date_joined")[:10]
    pending_tickets = Ticket.objects.filter(status__in=["OPEN", "IN_PROGRESS"]).count()
    pending_garages = Garage.objects.filter(
        approval_status=Garage.ApprovalStatus.PENDING
    ).count()

    users_this_month = User.objects.filter(date_joined__gte=thirty_days_ago).count()
    revenue_this_month = (
        Payment.objects.filter(
            status="SUCCESS", created_at__gte=thirty_days_ago
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    city_distribution = (
        Garage.objects.values("city__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:8]
    )
    garage_cities = City.objects.annotate(
        garage_count=Count(
            "garages", filter=Q(garages__approval_status=Garage.ApprovalStatus.APPROVED)
        )
    ).order_by("-garage_count")[:8]

    recent_payments = Payment.objects.filter(
        status="SUCCESS", created_at__gte=seven_days_ago
    ).count()

    alerts = []
    if pending_garages > 0:
        alerts.append(
            {
                "type": "warning",
                "title": _("Garages en attente de verification"),
                "message": f"{pending_garages} garage{pending_garages > 1 and 's' or ''} en attente",
                "link": reverse("administration:garages") + "?status=PENDING",
            }
        )
    if pending_tickets > 0:
        alerts.append(
            {
                "type": "warning",
                "title": _("Tickets ouverts"),
                "message": f"{pending_tickets} ticket{pending_tickets > 1 and 's' or ''} ouvert{pending_tickets > 1 and 's' or ''}",
                "link": reverse("administration:support"),
            }
        )

    latest_payments = (
        Payment.objects.filter(status="SUCCESS")
        .select_related("garage", "user")
        .order_by("-created_at")[:8]
    )

    context = {
        "total_users": total_users,
        "total_garages": total_garages,
        "verified_garages": verified_garages,
        "total_parts": total_parts,
        "total_payments": total_payments,
        "total_revenue": total_revenue,
        "recent_users": recent_users,
        "pending_tickets": pending_tickets,
        "pending_garages": pending_garages,
        "users_this_month": users_this_month,
        "revenue_this_month": revenue_this_month,
        "city_distribution": city_distribution,
        "garage_cities": garage_cities,
        "recent_payments": recent_payments,
        "latest_payments": latest_payments,
        "alerts": alerts,
    }
    return render(request, "dashboard/pages/admin/dashboard.html", context)



@user_passes_test(is_admin)
def admin_geography_view(request):
    cities = City.objects.annotate(
        garage_count=Count(
            "garages", filter=Q(garages__approval_status=Garage.ApprovalStatus.APPROVED)
        ),
        neighborhood_count=Count("neighborhoods"),
    ).order_by("-garage_count", "name")

    context = {
        "cities": cities,
    }
    return render(request, "dashboard/pages/admin/geography/geography.html", context)


@user_passes_test(is_admin)
def admin_users_view(request):
    users = User.objects.all().order_by("-date_joined")

    role = request.GET.get("role", "")
    search = request.GET.get("q", "")
    status = request.GET.get("status", "")

    if role:
        users = users.filter(role=role)
    if search:
        users = users.filter(
            Q(username__icontains=search)
            | Q(email__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
        )
    if status == "active":
        users = users.filter(account_status=User.AccountStatus.ACTIVE)
    elif status == "inactive":
        users = users.filter(account_status=User.AccountStatus.SUSPENDED)

    paginator = Paginator(users, 20)
    page = request.GET.get("page")
    users_page = paginator.get_page(page)

    return render(
        request,
        "dashboard/pages/admin/users/list.html",
        {
            "users": users_page,
            "selected_role": role,
            "search_query": search,
            "selected_status": status,
        },
    )


@user_passes_test(is_admin)
def admin_user_detail_view(request, user_id):
    user_obj = get_object_or_404(User, pk=user_id)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "toggle_active":
            if user_obj.pk == request.user.pk or user_obj.is_admin_or_above:
                messages.error(request, _("Vous ne pouvez pas suspendre ce compte."))
            else:
                from accounts.models import User as AccountUser

                user_obj.account_status = (
                    AccountUser.AccountStatus.SUSPENDED
                    if user_obj.account_status == AccountUser.AccountStatus.ACTIVE
                    else AccountUser.AccountStatus.ACTIVE
                )
                user_obj.save(update_fields=["account_status", "updated_at"])
                messages.success(request, _("Statut utilisateur mis à jour."))
        elif action == "change_role":
            new_role = request.POST.get("role")
            if new_role in ["USER", "CLIENT", "ADMIN"]:
                user_obj.role = new_role
                user_obj.save(update_fields=["role"])
                messages.success(request, _("Rôle utilisateur mis à jour."))
        return redirect("administration:user_detail", user_id=user_obj.pk)

    context = {
        "user_obj": user_obj,
        "user_payments": Payment.objects.filter(user=user_obj)[:10],
    }
    return render(request, "dashboard/pages/admin/user_detail.html", context)


@user_passes_test(is_admin)
def admin_garages_view(request):
    garages = Garage.objects.all().select_related("owner").order_by("-created_at")

    status = request.GET.get("status", "")
    payment_status = request.GET.get("payment_status", "")
    activation_status = request.GET.get("activation_status", "")
    search = request.GET.get("q", "")

    if status:
        if status == Garage.ActivationStatus.SUSPENDED:
            garages = garages.filter(activation_status=status)
        else:
            garages = garages.filter(approval_status=status)
    if payment_status:
        garages = garages.filter(payment_status=payment_status)
    if activation_status:
        garages = garages.filter(activation_status=activation_status)
    if search:
        garages = garages.filter(
            Q(name__icontains=search)
            | Q(owner__username__icontains=search)
            | Q(city__name__icontains=search)
        )

    paginator = Paginator(garages, 20)
    page = request.GET.get("page")
    garages_page = paginator.get_page(page)

    return render(
        request,
        "dashboard/pages/admin/garages/list.html",
        {
            "garages": garages_page,
            "selected_status": status,
            "selected_payment_status": payment_status,
            "selected_activation_status": activation_status,
            "search_query": search,
        },
    )


@user_passes_test(is_admin)
def admin_garage_verify_view(request, garage_id):
    from garages.services import (
        activate_garage,
        approve_garage,
        deactivate_garage,
        reject_garage,
        suspend_garage,
    )

    garage = get_object_or_404(Garage.objects.select_related("owner"), pk=garage_id)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "verify":
            result = approve_garage(garage, admin_user=request.user)
            messages.success(request, result["message"])
        elif action == "reject":
            reason = request.POST.get("rejection_reason", "").strip()
            result = reject_garage(garage, reason=reason, admin_user=request.user)
            messages.warning(request, result["message"])
        elif action == "suspend":
            result = suspend_garage(garage, admin_user=request.user)
            messages.warning(request, result["message"])
        elif action == "activate":
            result = activate_garage(garage, admin_user=request.user)
            if result["success"]:
                messages.success(request, result["message"])
            else:
                messages.error(request, result["message"])
        elif action == "deactivate":
            result = deactivate_garage(garage, admin_user=request.user)
            messages.warning(request, result["message"])

        return redirect("administration:garage_verify", garage_id=garage.pk)

    verifications = garage.verifications.select_related("verified_by").order_by(
        "-created_at"
    )

    return render(
        request,
        "dashboard/pages/admin/garages/verify.html",
        {
            "garage": garage,
            "verifications": verifications,
        },
    )


@user_passes_test(is_admin)
def admin_cities_view(request):
    cities = City.objects.annotate(
        garage_count=Count(
            "garages", filter=Q(garages__approval_status=Garage.ApprovalStatus.APPROVED)
        ),
        neighborhood_count=Count("neighborhoods"),
    ).order_by("name")

    search = request.GET.get("q", "")
    if search:
        cities = cities.filter(Q(name__icontains=search) | Q(slug__icontains=search))

    paginator = Paginator(cities, 20)
    page = request.GET.get("page")
    cities_page = paginator.get_page(page)

    return render(
        request,
        "dashboard/pages/admin/cities/list.html",
        {
            "cities": cities_page,
            "search_query": search,
        },
    )


@user_passes_test(is_admin)
def admin_city_create_view(request):
    if request.method == "POST":
        form = CityForm(request.POST)
        if form.is_valid():
            city = form.save()
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": True,
                        "message": _("Ville créée avec succès."),
                        "redirect": reverse("administration:cities"),
                    }
                )
            messages.success(request, _("Ville créée avec succès."))
            return redirect("administration:cities")
        else:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": False,
                        "errors": {
                            field: str(errs[0]) for field, errs in form.errors.items()
                        },
                    },
                    status=400,
                )
    else:
        form = CityForm()

    return render(
        request,
        "dashboard/pages/admin/cities/form.html",
        {
            "form": form,
            "is_new": True,
        },
    )


@user_passes_test(is_admin)
def admin_city_edit_view(request, city_id):
    city = get_object_or_404(City, pk=city_id)

    if request.method == "POST":
        form = CityForm(request.POST, instance=city)
        if form.is_valid():
            city = form.save()
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": True,
                        "message": _("Ville mise à jour avec succès."),
                        "redirect": reverse("administration:cities"),
                    }
                )
            messages.success(request, _("Ville mise à jour avec succès."))
            return redirect("administration:cities")
        else:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": False,
                        "errors": {
                            field: str(errs[0]) for field, errs in form.errors.items()
                        },
                    },
                    status=400,
                )
    else:
        form = CityForm(instance=city)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse(
            {
                "success": True,
                "form": {
                    "name": city.name,
                    "is_active": city.is_active,
                },
            }
        )

    return render(
        request,
        "dashboard/pages/admin/cities/form.html",
        {
            "form": form,
            "city": city,
            "is_new": False,
        },
    )


@user_passes_test(is_admin)
@require_POST
def admin_city_delete_view(request, city_id):
    city = get_object_or_404(City, pk=city_id)
    city_name = city.name

    garage_count = Garage.objects.filter(city=city).count()
    if garage_count > 0:
        msg = _(
            "Impossible de supprimer cette ville : %(count)s garage(x) associé(s)."
        ) % {"count": garage_count}
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "message": msg}, status=400)
        messages.error(request, msg)
        return redirect("administration:cities")

    city.delete()

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse(
            {
                "success": True,
                "message": _("Ville supprimée."),
                "redirect": reverse("administration:cities"),
            }
        )

    messages.success(request, _("Ville supprimée."))
    return redirect("administration:cities")


@user_passes_test(is_admin)
def admin_neighborhoods_view(request):
    neighborhoods = Neighborhood.objects.select_related("city").order_by(
        "city__name", "name"
    )

    search = request.GET.get("q", "")
    city_id = request.GET.get("city", "")
    if search:
        neighborhoods = neighborhoods.filter(
            Q(name__icontains=search) | Q(city__name__icontains=search)
        )
    if city_id:
        neighborhoods = neighborhoods.filter(city_id=city_id)

    cities = City.objects.order_by("name")

    paginator = Paginator(neighborhoods, 20)
    page = request.GET.get("page")
    neighborhoods_page = paginator.get_page(page)

    return render(
        request,
        "dashboard/pages/admin/neighborhoods/list.html",
        {
            "neighborhoods": neighborhoods_page,
            "cities": cities,
            "selected_city": city_id,
            "search_query": search,
        },
    )


@user_passes_test(is_admin)
def admin_neighborhood_create_view(request):
    if request.method == "POST":
        form = NeighborhoodForm(request.POST)
        if form.is_valid():
            neighborhood = form.save()
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": True,
                        "message": _("Quartier créé avec succès."),
                        "redirect": reverse("administration:neighborhoods"),
                    }
                )
            messages.success(request, _("Quartier créé avec succès."))
            return redirect("administration:neighborhoods")
        else:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": False,
                        "errors": {
                            field: str(errs[0]) for field, errs in form.errors.items()
                        },
                    },
                    status=400,
                )
    else:
        form = NeighborhoodForm()

    cities = City.objects.order_by("name")
    return render(
        request,
        "dashboard/pages/admin/neighborhoods/form.html",
        {
            "form": form,
            "cities": cities,
            "is_new": True,
        },
    )


@user_passes_test(is_admin)
def admin_neighborhood_edit_view(request, neighborhood_id):
    neighborhood = get_object_or_404(Neighborhood, pk=neighborhood_id)

    if request.method == "POST":
        form = NeighborhoodForm(request.POST, instance=neighborhood)
        if form.is_valid():
            neighborhood = form.save()
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": True,
                        "message": _("Quartier mis à jour avec succès."),
                        "redirect": reverse("administration:neighborhoods"),
                    }
                )
            messages.success(request, _("Quartier mis à jour avec succès."))
            return redirect("administration:neighborhoods")
        else:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": False,
                        "errors": {
                            field: str(errs[0]) for field, errs in form.errors.items()
                        },
                    },
                    status=400,
                )
    else:
        form = NeighborhoodForm(instance=neighborhood)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse(
            {
                "success": True,
                "form": {
                    "name": neighborhood.name,
                    "city": str(neighborhood.city_id) if neighborhood.city_id else "",
                    "is_active": neighborhood.is_active,
                },
                "cities": [
                    {"id": str(c.pk), "name": c.name}
                    for c in City.objects.order_by("name")
                ],
            }
        )

    cities = City.objects.order_by("name")
    return render(
        request,
        "dashboard/pages/admin/neighborhoods/form.html",
        {
            "form": form,
            "neighborhood": neighborhood,
            "cities": cities,
            "is_new": False,
        },
    )


@user_passes_test(is_admin)
@require_POST
def admin_neighborhood_delete_view(request, neighborhood_id):
    neighborhood = get_object_or_404(Neighborhood, pk=neighborhood_id)
    name = neighborhood.name

    garage_count = Garage.objects.filter(neighborhood=neighborhood).count()
    if garage_count > 0:
        msg = _(
            "Impossible de supprimer ce quartier : %(count)s garage(x) associé(s)."
        ) % {"count": garage_count}
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "message": msg}, status=400)
        messages.error(request, msg)
        return redirect("administration:neighborhoods")

    neighborhood.delete()

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse(
            {
                "success": True,
                "message": _("Quartier supprimé."),
                "redirect": reverse("administration:neighborhoods"),
            }
        )

    messages.success(request, _("Quartier supprimé."))
    return redirect("administration:neighborhoods")


@user_passes_test(is_admin)
def admin_payments_view(request):
    payments = (
        Payment.objects.all()
        .select_related("garage", "garage__owner", "user")
        .order_by("-created_at")
    )

    status = request.GET.get("status", "")
    provider = request.GET.get("provider", "")
    garage_id = request.GET.get("garage", "")
    client = request.GET.get("client", "").strip()
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    if status:
        payments = payments.filter(status=status)
    if provider:
        payments = payments.filter(provider=provider)
    if garage_id:
        payments = payments.filter(garage_id=garage_id)
    if client:
        payments = payments.filter(
            Q(user__username__icontains=client)
            | Q(user__email__icontains=client)
            | Q(garage__owner__username__icontains=client)
        )
    if date_from:
        payments = payments.filter(created_at__date__gte=date_from)
    if date_to:
        payments = payments.filter(created_at__date__lte=date_to)

    paginator = Paginator(payments, 20)
    page = request.GET.get("page")
    payments_page = paginator.get_page(page)

    return render(
        request,
        "dashboard/pages/admin/payments/list.html",
        {
            "payments": payments_page,
            "selected_status": status,
            "selected_provider": provider,
            "selected_garage": garage_id,
            "selected_client": client,
            "date_from": date_from,
            "date_to": date_to,
            "garages": Garage.objects.order_by("name"),
            "provider_choices": Payment.Provider.choices,
            "approved_unpaid_count": Garage.objects.filter(
                approval_status=Garage.ApprovalStatus.APPROVED,
                payment_status=Garage.PaymentStatus.UNPAID,
            ).count(),
            "paid_garage_count": Garage.objects.filter(
                payment_status=Garage.PaymentStatus.PAID
            ).count(),
            "active_garage_count": Garage.objects.filter(
                activation_status=Garage.ActivationStatus.ACTIVE
            ).count(),
            "suspended_garage_count": Garage.objects.filter(
                activation_status=Garage.ActivationStatus.SUSPENDED
            ).count(),
        },
    )


@user_passes_test(is_admin)
def admin_payment_detail_view(request, payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related("garage", "garage__owner", "user"),
        pk=payment_id,
    )
    receipt = getattr(payment, "receipt", None)
    return render(
        request,
        "dashboard/pages/admin/payments/detail.html",
        {
            "payment": payment,
            "receipt": receipt,
        },
    )


@user_passes_test(is_admin)
def admin_receipt_detail_view(request, receipt_id):
    receipt = get_object_or_404(
        Receipt.objects.select_related("payment", "garage", "owner"), pk=receipt_id
    )
    return render(
        request, "dashboard/pages/admin/payments/receipt.html", {"receipt": receipt}
    )


@user_passes_test(is_admin)
def admin_support_view(request):
    from support.models import Conversation, Message

    tickets = (
        Ticket.objects.all()
        .select_related("user", "assigned_to", "garage", "part")
        .order_by("-created_at")
    )

    conversations = Conversation.objects.prefetch_related(
        "participants", "messages__sender"
    ).order_by("-updated_at")

    status = request.GET.get("status", "")
    category = request.GET.get("category", "")
    search = request.GET.get("q", "").strip()
    tab = request.GET.get("tab", "tickets")

    if status:
        tickets = tickets.filter(status=status)
    if category:
        tickets = tickets.filter(category=category)
    if search:
        tickets = tickets.filter(
            Q(ticket_number__icontains=search)
            | Q(subject__icontains=search)
            | Q(user__username__icontains=search)
            | Q(user__email__icontains=search)
            | Q(description__icontains=search)
        )
        conversations = conversations.filter(
            Q(subject__icontains=search)
            | Q(participants__username__icontains=search)
            | Q(participants__email__icontains=search)
            | Q(messages__body__icontains=search)
        ).distinct()

    for conv in conversations:
        conv.last_message = conv.messages.select_related("sender").order_by(
            "-created_at"
        ).first()
        conv.unread_count = conv.unread_count_for(request.user)

    paginator = Paginator(tickets, 20)
    page = request.GET.get("page")
    tickets_page = paginator.get_page(page)

    conv_paginator = Paginator(conversations, 20)
    conv_page = conv_paginator.get_page(request.GET.get("conv_page"))

    return render(
        request,
        "dashboard/pages/admin/support/tickets/list.html",
        {
            "tickets": tickets_page,
            "conversations": conv_page,
            "selected_status": status,
            "selected_category": category,
            "search_query": search,
            "active_tab": tab,
        },
    )


@user_passes_test(is_admin)
def admin_ticket_detail_view(request, ticket_id):
    ticket = get_object_or_404(
        Ticket.objects.select_related("user", "garage", "part", "assigned_to"),
        pk=ticket_id,
    )
    from support.services import get_or_create_ticket_conversation

    conversation = get_or_create_ticket_conversation(ticket)
    ticket_messages = conversation.messages.select_related("sender").order_by(
        "created_at"
    )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "assign":
            ticket.assigned_to = request.user
            ticket.status = Ticket.Status.IN_PROGRESS
            ticket.save(update_fields=["assigned_to", "status", "updated_at"])
            messages.success(request, _("Ticket pris en charge."))

        elif action == "resolve":
            ticket.status = Ticket.Status.RESOLVED
            ticket.resolved_at = timezone.now()
            ticket.save(update_fields=["status", "resolved_at", "updated_at"])
            messages.success(request, _("Ticket résolu."))

        elif action == "close":
            ticket.status = Ticket.Status.CLOSED
            ticket.save(update_fields=["status", "updated_at"])
            messages.success(request, _("Ticket fermé."))

        elif action == "waiting":
            ticket.status = Ticket.Status.WAITING_CLIENT
            ticket.save(update_fields=["status", "updated_at"])
            messages.success(request, _("Statut mis à jour : en attente du client."))

        elif action == "reply":
            content = request.POST.get("content", "").strip()
            if content:
                from support.services import (
                    get_or_create_ticket_conversation,
                    send_message,
                )

                conversation = get_or_create_ticket_conversation(ticket)
                send_message(conversation, request.user, content)
                ticket.save(update_fields=["updated_at"])
                messages.success(request, _("Réponse envoyée."))

        return redirect("administration:ticket_detail", ticket_id=ticket.pk)

    return render(
        request,
        "dashboard/pages/admin/support/tickets/detail.html",
        {
            "ticket": ticket,
            "ticket_messages": ticket_messages,
            "conversation": conversation,
        },
    )


@user_passes_test(is_admin)
def admin_ticket_create_view(request):
    """Créer un ticket de support depuis l'administration, adressé
    soit à un utilisateur, soit à une boutique (garage)."""
    from support.forms import AdminTicketCreateForm
    from support.services import get_or_create_ticket_conversation, send_message
    from accounts.models import Notification

    if request.method == "POST":
        form = AdminTicketCreateForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data

            if data["recipient_type"] == "GARAGE":
                garage = data["garage"]
                ticket_user = garage.owner
                recipient_label = garage.name
            else:
                garage = None
                ticket_user = data["user"]
                recipient_label = ticket_user.display_name

            ticket = Ticket.objects.create(
                user=ticket_user,
                garage=garage,
                category=data["category"],
                subject=data["subject"],
                description=data["description"],
            )

            # Conversation liée au ticket + premier message envoyé par l'admin
            try:
                conversation = get_or_create_ticket_conversation(ticket)
                send_message(conversation, request.user, data["description"])
            except Exception:
                pass  # le ticket existe déjà ; la conversation pourra être recréée

            Notification.objects.create(
                user=ticket_user,
                notif_type=Notification.Type.TICKET_REPLY,
                title=_("Message du support : %(subject)s") % {"subject": ticket.subject},
                message=data["description"],
                link=f"/support/tickets/{ticket.ticket_number}/",
            )

            messages.success(
                request,
                _("Ticket %(number)s créé et envoyé à %(recipient)s.")
                % {"number": ticket.ticket_number, "recipient": recipient_label},
            )
            return redirect("administration:ticket_detail", ticket_id=ticket.pk)
        messages.error(request, _("Veuillez corriger les erreurs du formulaire."))
    else:
        form = AdminTicketCreateForm()

    return render(
        request,
        "dashboard/pages/admin/support/tickets/create.html",
        {"form": form},
    )


@user_passes_test(is_admin)
@user_passes_test(is_admin)
@require_POST
def admin_send_urgent_message_view(request, user_id):
    """Send an urgent direct message from admin to a user (garage owner)."""
    from support.services import get_or_create_conversation, send_message
    from accounts.models import Notification

    target_user = get_object_or_404(User, pk=user_id)
    subject = request.POST.get("subject", "").strip()
    content = request.POST.get("content", "").strip()

    if not content:
        messages.error(request, _("Le message ne peut pas etre vide."))
        return redirect("administration:user_detail", user_id=user_id)

    try:
        conversation = get_or_create_conversation(
            request.user, target_user, subject or "Message urgent de l'administration"
        )
        send_message(conversation, request.user, content)

        Notification.objects.create(
            user=target_user,
            notif_type=Notification.Type.ADMIN_MESSAGE,
            title=subject or "Message urgent de l'administration",
            message=content,
            link="/messages/%s/" % conversation.pk,
        )

        messages.success(
            request,
            _("Message urgent envoye a %(user)s.") % {"user": target_user.display_name},
        )
    except Exception as e:
        messages.error(
            request,
            _("Erreur lors de l'envoi : %(error)s") % {"error": str(e)},
        )

    return redirect("administration:user_detail", user_id=user_id)
