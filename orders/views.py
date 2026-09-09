from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import models, transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from catalog.models import Part

from . import services
from .forms import CheckoutForm, OrderCancelForm
from .models import Cart, CartItem, Order, OrderItem


@login_required
def cart_view(request):
    cart, _created = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related("part", "part__garage", "part__category")
    subtotal = cart.total
    service_fee = int(subtotal * Decimal("0.05"))
    total = subtotal + service_fee
    return render(
        request,
        "dashboard/pages/client/cart.html",
        {
            "cart": cart,
            "items": items,
            "subtotal": subtotal,
            "service_fee": service_fee,
            "total": total,
        },
    )


@login_required
def cart_add_view(request, part_id):
    part = get_object_or_404(Part, pk=part_id, is_active=True)
    cart, _created = Cart.objects.get_or_create(user=request.user)

    if not part.is_available:
        messages.error(request, _("Cette pièce n'est pas disponible."))
        return redirect("catalog:part_detail", slug=part.slug)

    # Get quantity from form (detail page) or default to 1
    try:
        quantity = int(request.POST.get("quantity", 1))
    except (ValueError, TypeError):
        quantity = 1
    quantity = max(1, min(quantity, part.stock))

    item, created = CartItem.objects.get_or_create(cart=cart, part=part)
    if not created:
        new_qty = item.quantity + quantity
        if new_qty <= part.stock:
            item.quantity = new_qty
            item.save()
        else:
            messages.warning(request, _("Stock maximum atteint pour cette pièce."))
    else:
        item.quantity = quantity
        item.save()
        messages.success(request, _("%(name)s ajouté au panier.") % {"name": part.name})
    return redirect("orders:cart")


@login_required
def cart_remove_view(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    item.delete()
    messages.success(request, _("Item removed from cart."))
    return redirect("orders:cart")


@login_required
def cart_update_view(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    try:
        quantity = int(request.POST.get("quantity", 1))
    except (ValueError, TypeError):
        quantity = 1
    if quantity <= 0:
        item.delete()
    elif quantity <= item.part.stock:
        item.quantity = quantity
        item.save()
    else:
        messages.warning(request, _("Insufficient stock."))
    return redirect("orders:cart")


@login_required
def checkout_view(request):
    cart = Cart.objects.filter(user=request.user).first()
    if not cart or not cart.items.exists():
        messages.warning(request, _("Your cart is empty."))
        return redirect("catalog:part_list")

    items = cart.items.select_related("part", "part__garage")
    vehicles = request.user.vehicles.all()
    subtotal = cart.total
    service_fee = int(subtotal * Decimal("0.05"))
    total = subtotal + service_fee

    if request.method == "POST":
        form = CheckoutForm(request.POST, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                order = Order(
                    user=request.user,
                    fulfillment_type=form.cleaned_data["fulfillment_type"],
                    subtotal=subtotal,
                    service_fee=service_fee,
                    total=total,
                    notes=form.cleaned_data.get("notes", ""),
                    delivery_address=form.cleaned_data.get("delivery_address", ""),
                    delivery_notes=form.cleaned_data.get("delivery_notes", ""),
                )
                vehicle = form.cleaned_data.get("vehicle")
                if vehicle:
                    order.vehicle = vehicle
                first_item = items.first()
                if first_item and first_item.part.garage:
                    order.garage = first_item.part.garage
                order.save()

                for item in items:
                    part = Part.objects.select_for_update().get(pk=item.part.pk)
                    if part.stock < item.quantity:
                        messages.error(
                            request,
                            _("Insufficient stock for %(name)s.") % {"name": part.name},
                        )
                        return redirect("orders:cart")

                    OrderItem.objects.create(
                        order=order,
                        part=part,
                        part_name=part.name,
                        part_price=part.price,
                        quantity=item.quantity,
                        subtotal=item.subtotal,
                        install_service=part.garage is not None,
                    )
                    part.stock -= item.quantity
                    part.save(update_fields=["stock"])

                cart.items.all().delete()

            from notifications.services import notify_new_order

            notify_new_order(order)
            messages.success(
                request, _("Order %(number)s created.") % {"number": order.order_number}
            )
            return redirect("orders:order_detail", order_number=order.order_number)
    else:
        form = CheckoutForm(user=request.user)

    return render(
        request,
        "dashboard/pages/client/orders/checkout.html",
        {
            "form": form,
            "cart": cart,
            "items": items,
            "vehicles": vehicles,
            "subtotal": subtotal,
            "service_fee": service_fee,
            "total": total,
        },
    )


@login_required
def order_list_view(request):
    """Liste des commandes de l'utilisateur (acheteur)."""
    orders = (
        Order.objects.filter(user=request.user)
        .select_related("garage", "vehicle")
        .prefetch_related("items")
    )

    status_filter = request.GET.get("status", "")
    garage_filter = request.GET.get("garage", "")
    q = request.GET.get("q", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    if status_filter:
        orders = orders.filter(status=status_filter)
    if garage_filter:
        orders = orders.filter(garage_id=garage_filter)
    if q:
        orders = orders.filter(order_number__icontains=q)
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)

    paginator = Paginator(orders, 15)
    orders_page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "dashboard/pages/client/orders/list.html",
        {
            "orders": orders_page,
            "status_filter": status_filter,
            "garage_filter": garage_filter,
            "q": q,
            "date_from": date_from,
            "date_to": date_to,
            "garages": Order.objects.filter(user=request.user)
            .exclude(garage=None)
            .values_list("garage_id", "garage__name")
            .distinct(),
            "status_choices": Order.Status.choices,
        },
    )


@login_required
def order_detail_view(request, order_number):
    """Détail d'une commande (acheteur, propriétaire du garage ou admin)."""
    order = get_object_or_404(
        Order.objects.select_related("garage", "garage__owner", "user", "vehicle"),
        order_number=order_number,
    )
    if not order.is_viewable_by(request.user):
        raise Http404(_("Commande introuvable."))

    items = order.items.select_related("part")
    allowed_actions = services.available_actions(order, request.user)
    is_garage_viewer = (
        order.garage is not None and order.garage.owner_id == request.user.pk
    )

    return render(
        request,
        "dashboard/pages/client/orders/detail.html",
        {
            "order": order,
            "items": items,
            "cancel_form": OrderCancelForm(),
            "allowed_actions": allowed_actions,
            "can_cancel": services.can_perform(order, "CANCEL", request.user),
            "is_garage_viewer": is_garage_viewer,
        },
    )


@login_required
def order_cancel_view(request, order_number):
    """Annulation contrôlée côté backend via la couche service."""
    order = get_object_or_404(Order, order_number=order_number)
    if not order.is_viewable_by(request.user):
        raise Http404(_("Commande introuvable."))

    form = OrderCancelForm(request.POST or None)
    if not form.is_valid():
        messages.error(request, _("Veuillez fournir une raison pour l'annulation."))
        return redirect("orders:order_detail", order_number=order_number)

    reason = form.cleaned_data["cancel_reason"]
    try:
        with transaction.atomic():
            order.cancel_reason = reason
            services.apply_transition(order, "CANCEL", request.user, note=reason)
            for item in order.items.select_related("part").all():
                if item.part:
                    Part.objects.filter(pk=item.part.pk).update(
                        stock=models.F("stock") + item.quantity
                    )
        messages.success(request, _("Commande annulée."))
    except PermissionDenied as exc:
        messages.error(request, str(exc))
    return redirect("orders:order_detail", order_number=order_number)


def _order_action_post(action, success_msg):
    def view(request, order_number):
        if request.method != "POST":
            return redirect("orders:order_detail", order_number=order_number)
        order = get_object_or_404(Order, order_number=order_number)
        if not order.is_viewable_by(request.user):
            raise Http404(_("Commande introuvable."))
        try:
            services.apply_transition(
                order, action, request.user, note=request.POST.get("note", "")
            )
            messages.success(request, success_msg)
        except PermissionDenied as exc:
            messages.error(request, str(exc))
        return redirect("orders:order_detail", order_number=order_number)

    return login_required(view)


order_confirm_view = _order_action_post("CONFIRM", _("Commande confirmée."))
order_mark_ready_view = _order_action_post(
    "MARK_READY", _("Commande marquée comme prête.")
)
order_mark_delivered_view = _order_action_post(
    "MARK_DELIVERED", _("Commande marquée comme livrée.")
)
order_confirm_receipt_view = _order_action_post(
    "CONFIRM_RECEIPT", _("Réception confirmée. Merci !")
)


@login_required
def garage_orders_view(request):
    """Liste des commandes des garages du propriétaire (client/garage)."""
    from garages.models import Garage

    garages = Garage.objects.filter(owner=request.user)
    if not garages.exists():
        messages.warning(request, _("Aucun garage associé à votre compte."))
        return redirect("garages:garage_create")

    orders = (
        Order.objects.filter(garage__in=garages)
        .select_related("garage", "user", "vehicle")
        .prefetch_related("items")
    )

    status_filter = request.GET.get("status", "")
    garage_filter = request.GET.get("garage", "")
    client_filter = request.GET.get("client", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    if status_filter:
        orders = orders.filter(status=status_filter)
    if garage_filter:
        orders = orders.filter(garage_id=garage_filter)
    if client_filter:
        orders = orders.filter(user__username__icontains=client_filter)
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)

    paginator = Paginator(orders, 15)
    orders_page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "dashboard/pages/garage/orders/list.html",
        {
            "orders": orders_page,
            "garages": garages,
            "status_filter": status_filter,
            "garage_filter": garage_filter,
            "client_filter": client_filter,
            "date_from": date_from,
            "date_to": date_to,
            "status_choices": Order.Status.choices,
        },
    )


@login_required
def direct_order_view(request, part_id):
    """
    Direct order for a single part from a single garage.
    1 order = 1 user, 1 garage, 1 part.
    """
    part = get_object_or_404(
        Part.objects.select_related("garage"), pk=part_id, is_active=True
    )

    if not part.garage:
        messages.error(request, _("Cette pièce n'est pas liée à un garage."))
        return redirect("catalog:part_detail", slug=part.slug)

    if not part.is_available:
        messages.error(request, _("Cette pièce n'est plus disponible."))
        return redirect("catalog:part_detail", slug=part.slug)

    if request.method != "POST":
        return redirect("catalog:part_detail", slug=part.slug)

    try:
        quantity = int(request.POST.get("quantity", 1))
    except (ValueError, TypeError):
        quantity = 1

    if quantity < 1:
        messages.error(request, _("La quantité doit être supérieure à 0."))
        return redirect("catalog:part_detail", slug=part.slug)

    if quantity > part.stock:
        messages.error(
            request,
            _("Stock insuffisant. Disponible: %(stock)s.") % {"stock": part.stock},
        )
        return redirect("catalog:part_detail", slug=part.slug)

    try:
        with transaction.atomic():
            locked_part = Part.objects.select_for_update().get(pk=part.pk)

            if locked_part.stock < quantity:
                messages.error(
                    request,
                    _("Stock insuffisant. Disponible: %(stock)s.")
                    % {"stock": locked_part.stock},
                )
                return redirect("catalog:part_detail", slug=part.slug)

            unit_price = locked_part.price
            subtotal = unit_price * quantity

            order = Order(
                user=request.user,
                garage=locked_part.garage,
                subtotal=subtotal,
                total=subtotal,
                status=Order.Status.PENDING,
            )
            order.save()

            OrderItem.objects.create(
                order=order,
                part=locked_part,
                part_name=locked_part.name,
                part_price=unit_price,
                quantity=quantity,
                subtotal=subtotal,
            )

            locked_part.stock -= quantity
            locked_part.save(update_fields=["stock"])
            locked_part.update_stock_status()

    except Exception as e:
        messages.error(
            request,
            _("Une erreur est survenue lors de la commande. Veuillez réessayer."),
        )
        return redirect("catalog:part_detail", slug=part.slug)

    from notifications.services import notify_new_order

    notify_new_order(order)

    messages.success(
        request,
        _("Commande %(number)s créée avec succès !") % {"number": order.order_number},
    )
    return redirect("orders:order_detail", order_number=order.order_number)
