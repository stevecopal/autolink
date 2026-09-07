from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator
from django.utils import timezone

from .models import Ticket, TicketMessage, AssistanceRequest
from .forms import TicketForm, TicketMessageForm, AssistanceRequestForm


@login_required
def ticket_list_view(request):
    tickets = Ticket.objects.filter(
        user=request.user
    ).select_related('order', 'garage', 'part', 'assigned_to').prefetch_related('messages').order_by('-created_at')

    status_filter = request.GET.get('status', '')
    if status_filter:
        tickets = tickets.filter(status=status_filter)

    paginator = Paginator(tickets, 15)
    page = request.GET.get('page')
    tickets_page = paginator.get_page(page)

    for ticket in tickets_page:
        last_msg = ticket.messages.order_by('-created_at').first()
        ticket.last_message = last_msg

    return render(request, 'dashboard/pages/client/support/tickets.html', {
        'tickets': tickets_page,
        'status_filter': status_filter,
    })


@login_required
def ticket_create_view(request):
    if request.method == 'POST':
        form = TicketForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user

            order = form.cleaned_data.get('order')
            part = form.cleaned_data.get('part')
            garage = form.cleaned_data.get('garage')

            if order and not garage:
                first_item = order.items.select_related('part__garage').first()
                if first_item and first_item.part and first_item.part.garage:
                    ticket.garage = first_item.part.garage

            if order and not part:
                first_item = order.items.select_related('part').first()
                if first_item and first_item.part:
                    ticket.part = first_item.part

            if part and not garage and part.garage:
                ticket.garage = part.garage

            ticket.save()

            attachment = request.FILES.get('attachment')
            if attachment:
                TicketMessage.objects.create(
                    ticket=ticket,
                    sender=request.user,
                    message=_('Ticket créé'),
                    attachment=attachment,
                )

            messages.success(request, _('Ticket %(number)s créé avec succès.') % {'number': ticket.ticket_number})
            return redirect('support:ticket_detail', ticket_number=ticket.ticket_number)
    else:
        form = TicketForm(user=request.user)

    return render(request, 'dashboard/pages/client/support/ticket_form.html', {
        'form': form,
    })


@login_required
def ticket_detail_view(request, ticket_number):
    ticket = get_object_or_404(
        Ticket.objects.select_related('order', 'garage', 'part', 'assigned_to'),
        ticket_number=ticket_number,
        user=request.user
    )
    messages_qs = ticket.messages.select_related('sender').order_by('created_at')

    if request.method == 'POST':
        action = request.POST.get('action', 'reply')

        if action == 'reopen':
            if ticket.status == Ticket.Status.CLOSED:
                ticket.status = Ticket.Status.OPEN
                ticket.save(update_fields=['status', 'updated_at'])
                messages.success(request, _('Ticket rouvert.'))
            return redirect('support:ticket_detail', ticket_number=ticket_number)

        if action == 'delete':
            ticket.delete()
            messages.success(request, _('Ticket supprimé.'))
            return redirect('support:ticket_list')

        form = TicketMessageForm(request.POST, request.FILES)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.ticket = ticket
            msg.sender = request.user
            msg.save()

            if ticket.status in (Ticket.Status.CLOSED, Ticket.Status.RESOLVED):
                ticket.status = Ticket.Status.OPEN
                ticket.save(update_fields=['status', 'updated_at'])

            return redirect('support:ticket_detail', ticket_number=ticket_number)
    else:
        form = TicketMessageForm()

    return render(request, 'dashboard/pages/client/support/ticket_detail.html', {
        'ticket': ticket,
        'messages': messages_qs,
        'form': form,
    })


def assistance_view(request):
    if request.method == 'POST':
        form = AssistanceRequestForm(request.POST)
        if form.is_valid():
            assistance = form.save(commit=False)
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            if latitude and longitude:
                assistance.latitude = latitude
                assistance.longitude = longitude
                if request.user.is_authenticated:
                    assistance.user = request.user
                assistance.save()
                messages.success(request, _('Demande d\'assistance envoyée.'))
                return redirect('support:assistance_confirm')
            messages.error(request, _('Position requise pour l\'assistance.'))
    else:
        form = AssistanceRequestForm()
    return render(request, 'dashboard/pages/client/support/assistance.html', {'form': form})


def assistance_confirm_view(request):
    return render(request, 'dashboard/pages/client/support/assistance_confirm.html')
