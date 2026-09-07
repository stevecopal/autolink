from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator

from .models import Ticket, TicketMessage, AssistanceRequest
from .forms import TicketForm, TicketMessageForm, AssistanceRequestForm


@login_required
def ticket_list_view(request):
    tickets = Ticket.objects.filter(user=request.user).order_by('-created_at')
    status_filter = request.GET.get('status', '')
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    
    paginator = Paginator(tickets, 15)
    page = request.GET.get('page')
    tickets_page = paginator.get_page(page)
    
    return render(request, 'dashboard/pages/client/support/tickets.html', {
        'tickets': tickets_page,
        'status_filter': status_filter,
    })


@login_required
def ticket_create_view(request):
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            ticket.save()
            messages.success(request, _('Ticket %(number)s created.') % {'number': ticket.ticket_number})
            return redirect('support:ticket_detail', ticket_number=ticket.ticket_number)
    else:
        form = TicketForm()
    return render(request, 'dashboard/pages/client/support/ticket_form.html', {'form': form})


@login_required
def ticket_detail_view(request, ticket_number):
    ticket = get_object_or_404(
        Ticket.objects.select_related('order', 'garage', 'assigned_to'),
        ticket_number=ticket_number,
        user=request.user
    )
    messages_qs = ticket.messages.select_related('sender').order_by('created_at')

    if request.method == 'POST':
        form = TicketMessageForm(request.POST, request.FILES)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.ticket = ticket
            msg.sender = request.user
            msg.save()
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
                messages.success(request, _('Assistance request sent.'))
                return redirect('support:assistance_confirm')
            messages.error(request, _('Position required for assistance.'))
    else:
        form = AssistanceRequestForm()
    return render(request, 'dashboard/pages/client/support/assistance.html', {'form': form})


def assistance_confirm_view(request):
    return render(request, 'dashboard/pages/client/support/assistance_confirm.html')
