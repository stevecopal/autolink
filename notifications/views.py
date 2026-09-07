from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Notification


@login_required
def notification_list_view(request):
    notifications = request.user.notifications.all()
    unread_count = notifications.filter(is_read=False).count()
    return render(request, 'dashboard/pages/client/notifications.html', {
        'notifications': notifications[:50],
        'unread_count': unread_count,
    })


@login_required
def notification_mark_read_view(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.mark_as_read()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok'})
    return redirect('notifications:notification_list')


@login_required
def notification_mark_all_read_view(request):
    if request.method == 'POST':
        request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect('notifications:notification_list')


@login_required
def notification_count_api(request):
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({'unread_count': count})
