from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list_view(request):
    notifications = request.user.notifications.all()
    unread_count = notifications.filter(is_read=False).count()
    page = Paginator(notifications, 50).get_page(request.GET.get("page"))
    return render(
        request,
        "dashboard/pages/client/notifications.html",
        {
            "notifications": page,
            "notifications_count": notifications.count(),
            "unread_count": unread_count,
            "page_obj": page,
            "is_paginated": page.has_other_pages(),
        },
    )


@login_required
@require_POST
def notification_mark_read_view(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.mark_as_read()
    return JsonResponse(
        {
            "success": True,
            "unread_count": request.user.notifications.filter(is_read=False).count(),
        }
    )


@login_required
def notification_mark_all_read_view(request):
    if request.method == "POST":
        request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect("notifications:notification_list")


@login_required
def notification_count_api(request):
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({"unread_count": count})
