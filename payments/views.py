from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.paginator import Paginator

from .models import Payment, Refund
from .forms import PaymentForm, RefundRequestForm
from orders.models import Order


@login_required
def payment_initiate_view(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    if order.status != Order.Status.PENDING:
        messages.error(request, _('This order can no longer be paid.'))
        return redirect('orders:order_detail', order_number=order_number)

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = Payment(
                order=order,
                user=request.user,
                amount=order.total,
                provider=form.cleaned_data['provider'],
                phone_number=form.cleaned_data.get('phone_number', ''),
                status=Payment.Status.INITIATED,
            )
            payment.save()

            messages.success(request, _('Payment initiated. You will receive a confirmation.'))
            return redirect('payments:payment_detail', payment_id=payment.pk)
    else:
        form = PaymentForm()

    return render(request, 'dashboard/pages/client/payments/initiate.html', {'order': order, 'form': form})


@login_required
def payment_detail_view(request, payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related('order'),
        pk=payment_id,
        user=request.user
    )
    return render(request, 'dashboard/pages/client/payments/detail.html', {'payment': payment})


@login_required
def payment_list_view(request):
    payments = Payment.objects.filter(user=request.user).select_related('order').order_by('-created_at')
    paginator = Paginator(payments, 15)
    page = request.GET.get('page')
    payments_page = paginator.get_page(page)
    return render(request, 'dashboard/pages/client/payments/list.html', {'payments': payments_page})


@login_required
def refund_request_view(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    if order.status not in ['PAID', 'PROCESSING', 'READY']:
        messages.error(request, _('Cannot request a refund for this order.'))
        return redirect('orders:order_detail', order_number=order_number)

    if request.method == 'POST':
        form = RefundRequestForm(request.POST)
        if form.is_valid():
            payment = order.payments.filter(status=Payment.Status.SUCCESS).first()
            if not payment:
                messages.error(request, _('No payment found for this order.'))
                return redirect('orders:order_detail', order_number=order_number)

            refund = Refund(
                payment=payment,
                order=order,
                user=request.user,
                amount=payment.amount,
                reason=form.cleaned_data['reason'],
            )
            refund.save()
            messages.success(request, _('Your refund request has been recorded.'))
            return redirect('payments:refund_detail', refund_id=refund.pk)
    else:
        form = RefundRequestForm()

    return render(request, 'dashboard/pages/client/payments/refund_request.html', {'order': order, 'form': form})


@login_required
def refund_detail_view(request, refund_id):
    refund = get_object_or_404(
        Refund.objects.select_related('order', 'payment'),
        pk=refund_id,
        user=request.user
    )
    return render(request, 'dashboard/pages/client/payments/refund_detail.html', {'refund': refund})
