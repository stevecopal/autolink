from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from .forms import AssistanceRequestForm, TicketForm, TicketMessageForm
from .models import AssistanceRequest, Conversation, Ticket, TicketMessage
from .services import (
    admin_users,
    can_access_conversation,
    get_or_create_ticket_conversation,
    mark_conversation_read,
    send_message,
)


def _conversation_queryset(user):
    queryset = Conversation.objects.prefetch_related("participants", "messages__sender")
    if user.is_admin_or_above:
        return queryset
    return queryset.filter(participants=user)


@login_required
def conversation_list_view(request):
    conversations = _conversation_queryset(request.user)
    for conversation in conversations:
        conversation.unread_count = conversation.unread_count_for(request.user)
    unread_count = sum(conversation.unread_count for conversation in conversations)
    return render(
        request,
        "dashboard/pages/client/messages/list.html",
        {
            "conversations": conversations,
            "unread_count": unread_count,
        },
    )


@login_required
@require_POST
def conversation_create_view(request):
    administrator = admin_users().first()
    if not administrator:
        messages.error(request, _("Aucun administrateur n'est disponible."))
        return redirect("support:conversation_list")
    conversation = Conversation.objects.create(
        subject=request.POST.get("subject", "Message à l'administration")
        or "Message à l'administration"
    )
    conversation.participants.add(request.user, administrator)
    return redirect("support:conversation_detail", conversation_id=conversation.pk)


@login_required
def conversation_detail_view(request, conversation_id):
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    if not can_access_conversation(conversation, request.user):
        from django.http import Http404

        raise Http404
    if request.method == "POST":
        body = request.POST.get("body", "").strip()
        if body or request.FILES.get("attachment"):
            send_message(
                conversation, request.user, body, request.FILES.get("attachment")
            )
            return redirect(
                "support:conversation_detail", conversation_id=conversation.pk
            )
        messages.error(request, _("Le message ne peut pas être vide."))
    mark_conversation_read(conversation, request.user)
    return render(
        request,
        "dashboard/pages/client/messages/detail.html",
        {
            "conversation": conversation,
            "conversation_messages": conversation.messages.select_related("sender"),
        },
    )


@login_required
def ticket_list_view(request):
    tickets = (
        Ticket.objects.filter(user=request.user)
        .select_related("garage", "part", "assigned_to")
        .prefetch_related("messages")
        .order_by("-created_at")
    )

    status_filter = request.GET.get("status", "")
    if status_filter:
        tickets = tickets.filter(status=status_filter)

    paginator = Paginator(tickets, 15)
    page = request.GET.get("page")
    tickets_page = paginator.get_page(page)

    for ticket in tickets_page:
        last_msg = ticket.messages.order_by("-created_at").first()
        ticket.last_message = last_msg

    return render(
        request,
        "dashboard/pages/client/support/tickets.html",
        {
            "tickets": tickets_page,
            "status_filter": status_filter,
        },
    )

@login_required
def ticket_create_view(request):
    if request.method == "POST":
        form = TicketForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            try:
                ticket = form.save(commit=False)
                ticket.user = request.user
                ticket.subject = ticket.description[:100]
                ticket.category = Ticket.Category.GARAGE

                if not ticket.garage:
                    messages.error(request, _("Vous devez sélectionner un garage."))
                    return render(
                        request,
                        "dashboard/pages/client/support/ticket_form.html",
                        {"form": form},
                    )

                ticket.save()

                conversation = get_or_create_ticket_conversation(ticket)
                send_message(
                    conversation, request.user, ticket.description, ticket.evidence
                )

                attachment = request.FILES.get("attachment")
                if attachment:
                    TicketMessage.objects.create(
                        ticket=ticket,
                        sender=request.user,
                        message=_("Ticket créé avec pièce jointe"),
                        attachment=attachment,
                    )

                messages.success(
                    request,
                    _("Ticket créé avec succès."),
                )
                return redirect("support:ticket_list")

            except Exception as e:
                messages.error(
                    request,
                    _("Une erreur est survenue : {error}").format(error=str(e)),
                )
                print(f"[ERROR] Erreur lors de la création du ticket : {e}")

    else:
        form = TicketForm(user=request.user)

    return render(
        request, "dashboard/pages/client/support/ticket_form.html", {"form": form}
    )


@login_required
def ticket_detail_view(request, ticket_number):
    ticket = get_object_or_404(
        Ticket.objects.select_related("garage", "part", "assigned_to"),
        ticket_number=ticket_number,
        user=request.user,
    )
    conversation = get_or_create_ticket_conversation(ticket)
    if not conversation.messages.exists():
        send_message(conversation, request.user, ticket.description, ticket.evidence)

    if request.method == "GET":
        return redirect("support:conversation_detail", conversation_id=conversation.pk)

    messages_qs = ticket.messages.select_related("sender").order_by("created_at")

    if request.method == "POST":
        action = request.POST.get("action", "reply")

        if action == "reopen":
            if ticket.status == Ticket.Status.CLOSED:
                ticket.status = Ticket.Status.OPEN
                ticket.save(update_fields=["status", "updated_at"])
                messages.success(request, _("Ticket rouvert."))
            return redirect("support:ticket_detail", ticket_number=ticket_number)

        if action == "delete":
            ticket.delete()
            messages.success(request, _("Ticket supprimé."))
            return redirect("support:ticket_list")

        form = TicketMessageForm(request.POST, request.FILES)
        if form.is_valid():
            send_message(
                conversation,
                request.user,
                form.cleaned_data["message"],
                form.cleaned_data.get("attachment"),
            )

            if ticket.status in (Ticket.Status.CLOSED, Ticket.Status.RESOLVED):
                ticket.status = Ticket.Status.OPEN
                ticket.save(update_fields=["status", "updated_at"])

            return redirect(
                "support:conversation_detail", conversation_id=conversation.pk
            )
    else:
        form = TicketMessageForm()

    return render(
        request,
        "dashboard/pages/client/support/ticket_detail.html",
        {
            "ticket": ticket,
            "messages": messages_qs,
            "form": form,
        },
    )


def assistance_view(request):
    if request.method == "POST":
        form = AssistanceRequestForm(request.POST)
        if form.is_valid():
            assistance = form.save(commit=False)
            latitude = request.POST.get("latitude")
            longitude = request.POST.get("longitude")
            if latitude and longitude:
                assistance.latitude = latitude
                assistance.longitude = longitude
                if request.user.is_authenticated:
                    assistance.user = request.user
                assistance.save()
                messages.success(request, _("Demande d'assistance envoyée."))
                return redirect("support:assistance_confirm")
            messages.error(request, _("Position requise pour l'assistance."))
    else:
        form = AssistanceRequestForm()
    return render(
        request, "dashboard/pages/client/support/assistance.html", {"form": form}
    )


def assistance_confirm_view(request):
    return render(request, "dashboard/pages/client/support/assistance_confirm.html")
