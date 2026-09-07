from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _

from .models import Vehicle, Brand, ModelVehicle
from .forms import VehicleForm


@login_required
def vehicle_list_view(request):
    vehicles = request.user.vehicles.select_related('brand', 'model')
    brands = Brand.objects.filter(is_active=True)
    return render(request, 'dashboard/pages/client/vehicles/list.html', {
        'vehicles': vehicles,
        'brands': brands,
    })


@login_required
def vehicle_add_view(request):
    if request.method == 'POST':
        form = VehicleForm(request.POST)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.user = request.user
            vehicle.save()
            messages.success(request, _('Vehicle added successfully.'))
            return redirect('vehicles:vehicle_list')
    else:
        form = VehicleForm()

    brands = Brand.objects.filter(is_active=True)
    return render(request, 'dashboard/pages/client/vehicles/form.html', {
        'form': form,
        'brands': brands,
        'action': 'add',
    })


@login_required
def vehicle_edit_view(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, user=request.user)
    if request.method == 'POST':
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            messages.success(request, _('Vehicle updated.'))
            return redirect('vehicles:vehicle_list')
    else:
        form = VehicleForm(instance=vehicle)

    brands = Brand.objects.filter(is_active=True)
    return render(request, 'dashboard/pages/client/vehicles/form.html', {
        'form': form,
        'vehicle': vehicle,
        'brands': brands,
        'action': 'edit',
    })


@login_required
def vehicle_delete_view(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, user=request.user)
    if request.method == 'POST':
        vehicle.delete()
        messages.success(request, _('Vehicle deleted.'))
        return redirect('vehicles:vehicle_list')
    return render(request, 'dashboard/pages/client/vehicles/confirm_delete.html', {'vehicle': vehicle})


@login_required
def vehicle_set_primary_view(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, user=request.user)
    if request.method == 'POST':
        vehicle.is_primary = True
        vehicle.save()
        messages.success(request, _('Vehicle set as primary.'))
    return redirect('vehicles:vehicle_list')


def api_models_by_brand(request, brand_id):
    models = ModelVehicle.objects.filter(brand_id=brand_id, is_active=True).values('id', 'name')
    return JsonResponse(list(models), safe=False)
