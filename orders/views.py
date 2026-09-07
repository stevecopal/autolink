from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction, models
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator

from .models import Cart, CartItem, Order, OrderItem
from .forms import CheckoutForm, OrderCancelForm
from catalog.models import Part


@login_required
def cart_view(request):
    cart, _created = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('part', 'part__garage')
    subtotal = cart.total
    service_fee = float(subtotal * 0.05)
    total = subtotal + service_fee
    return render(request, 'dashboard/pages/client/cart.html', {
        'cart': cart,
        'items': items,
        'subtotal': subtotal,
        'service_fee': service_fee,
        'total': total,
    })


@login_required
def cart_add_view(request, part_id):
    part = get_object_or_404(Part, pk=part_id, is_active=True)
    cart, _created = Cart.objects.get_or_create(user=request.user)

    if not part.is_available:
        messages.error(request, _('This part is not available.'))
        return redirect('catalog:part_detail', slug=part.slug)

    item, created = CartItem.objects.get_or_create(cart=cart, part=part)
    if not created:
        if item.quantity < part.stock:
            item.quantity += 1
            item.save()
        else:
            messages.warning(request, _('Maximum stock reached for this part.'))
    else:
        messages.success(request, _('%(name)s added to cart.') % {'name': part.name})
    return redirect('orders:cart')


@login_required
def cart_remove_view(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    item.delete()
    messages.success(request, _('Item removed from cart.'))
    return redirect('orders:cart')


@login_required
def cart_update_view(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1
    if quantity <= 0:
        item.delete()
    elif quantity <= item.part.stock:
        item.quantity = quantity
        item.save()
    else:
        messages.warning(request, _('Insufficient stock.'))
    return redirect('orders:cart')


@login_required
def checkout_view(request):
    cart = Cart.objects.filter(user=request.user).first()
    if not cart or not cart.items.exists():
        messages.warning(request, _('Your cart is empty.'))
        return redirect('catalog:part_list')

    items = cart.items.select_related('part', 'part__garage')
    vehicles = request.user.vehicles.all()
    subtotal = cart.total
    service_fee = int(subtotal * 0.05)
    total = subtotal + service_fee

    if request.method == 'POST':
        form = CheckoutForm(request.POST, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                order = Order(
                    user=request.user,
                    fulfillment_type=form.cleaned_data['fulfillment_type'],
                    subtotal=subtotal,
                    service_fee=service_fee,
                    total=total,
                    notes=form.cleaned_data.get('notes', ''),
                    delivery_address=form.cleaned_data.get('delivery_address', ''),
                    delivery_notes=form.cleaned_data.get('delivery_notes', ''),
                )
                vehicle = form.cleaned_data.get('vehicle')
                if vehicle:
                    order.vehicle = vehicle
                first_item = items.first()
                if first_item and first_item.part.garage:
                    order.garage = first_item.part.garage
                order.save()

                for item in items:
                    part = Part.objects.select_for_update().get(pk=item.part.pk)
                    if part.stock < item.quantity:
                        messages.error(request, _('Insufficient stock for %(name)s.') % {'name': part.name})
                        return redirect('orders:cart')

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
                    part.save(update_fields=['stock'])

                cart.items.all().delete()

            messages.success(request, _('Order %(number)s created.') % {'number': order.order_number})
            return redirect('orders:order_detail', order_number=order.order_number)
    else:
        form = CheckoutForm(user=request.user)

    return render(request, 'dashboard/pages/client/orders/checkout.html', {
        'form': form,
        'cart': cart,
        'items': items,
        'vehicles': vehicles,
        'subtotal': subtotal,
        'service_fee': service_fee,
        'total': total,
    })


@login_required
def order_list_view(request):
    orders = Order.objects.filter(user=request.user).select_related('garage')
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)

    paginator = Paginator(orders, 15)
    page = request.GET.get('page')
    orders_page = paginator.get_page(page)

    return render(request, 'dashboard/pages/client/orders/list.html', {
        'orders': orders_page,
        'status_filter': status_filter,
    })


@login_required
def order_detail_view(request, order_number):
    order = get_object_or_404(
        Order.objects.select_related('garage', 'vehicle'),
        order_number=order_number,
        user=request.user
    )
    items = order.items.select_related('part')
    cancel_form = OrderCancelForm()
    return render(request, 'dashboard/pages/client/orders/detail.html', {
        'order': order,
        'items': items,
        'cancel_form': cancel_form,
    })


@login_required
def order_cancel_view(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    if order.status in [Order.Status.PENDING, Order.Status.CONFIRMED]:
        form = OrderCancelForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                order.status = Order.Status.CANCELLED
                order.cancel_reason = form.cleaned_data['cancel_reason']
                order.save()
                for item in order.items.select_related('part').all():
                    if item.part:
                        Part.objects.filter(pk=item.part.pk).update(
                            stock=models.F('stock') + item.quantity
                        )
            messages.success(request, _('Order cancelled.'))
        else:
            messages.error(request, _('Please provide a reason for cancellation.'))
    else:
        messages.error(request, _('This order cannot be cancelled.'))
    return redirect('orders:order_detail', order_number=order_number)
