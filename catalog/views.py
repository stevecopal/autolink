from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator
from django.utils.text import slugify
from django.http import JsonResponse

from .models import Category, Part, Compatibility, PartRequest
from .forms import PartForm, PartRequestForm
from garages.models import Garage


def part_list_view(request):
    parts = Part.objects.filter(
        is_active=True,
        stock_status__in=[Part.StockStatus.IN_STOCK, Part.StockStatus.LOW_STOCK]
    ).select_related('category', 'brand', 'seller', 'garage')

    category_slug = request.GET.get('category', '')
    brand_id = request.GET.get('brand', '')
    condition = request.GET.get('condition', '')
    city = request.GET.get('city', '')
    search = request.GET.get('q', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    sort = request.GET.get('sort', '-created_at')

    if category_slug:
        parts = parts.filter(category__slug=category_slug)
    if brand_id:
        parts = parts.filter(brand_id=brand_id)
    if condition:
        parts = parts.filter(condition=condition)
    if city:
        parts = parts.filter(city__icontains=city)
    if search:
        parts = parts.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(reference_oem__icontains=search) |
            Q(reference_fabricant__icontains=search)
        )
    if min_price:
        try:
            parts = parts.filter(price__gte=float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            parts = parts.filter(price__lte=float(max_price))
        except ValueError:
            pass

    valid_sorts = {
        'price': 'price',
        '-price': '-price',
        'newest': '-created_at',
        '-created_at': '-created_at',
        'name': 'name',
    }
    parts = parts.order_by(valid_sorts.get(sort, '-created_at'))

    paginator = Paginator(parts, 10)
    page = request.GET.get('page')
    parts_page = paginator.get_page(page)

    categories = Category.objects.filter(parent=None, is_active=True)
    from vehicles.models import Brand
    brands = Brand.objects.filter(is_active=True, parts__isnull=False).distinct()

    return render(request, 'public/pages/catalog/part_list.html', {
        'parts': parts_page,
        'categories': categories,
        'brands': brands,
        'selected_category': category_slug,
        'selected_brand': brand_id,
        'selected_condition': condition,
        'search_query': search,
        'sort': sort,
    })


def part_detail_view(request, slug):
    part = get_object_or_404(
        Part.objects.select_related('category', 'brand', 'seller', 'garage'),
        slug=slug,
        is_active=True
    )
    compatibilities = part.compatibilities.select_related('brand', 'model_vehicle')
    photos = part.photos.all()

    context = {
        'part': part,
        'compatibilities': compatibilities,
        'photos': photos,
    }

    if request.user.is_authenticated:
        context['user_has_favorite'] = request.user.favorites.filter(
            part=part, object_type='PART'
        ).exists()
        context['user_vehicles'] = request.user.vehicles.all()
        if part.garage:
            context['similar_parts'] = Part.objects.filter(
                category=part.category,
                is_active=True,
                stock_status__in=[Part.StockStatus.IN_STOCK, Part.StockStatus.LOW_STOCK]
            ).exclude(pk=part.pk)[:6]

    return render(request, 'public/pages/catalog/part_detail.html', context)


def category_detail_view(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    parts = Part.objects.filter(
        category=category,
        is_active=True,
        stock_status__in=[Part.StockStatus.IN_STOCK, Part.StockStatus.LOW_STOCK]
    ).select_related('brand', 'seller', 'garage')
    children = category.children.filter(is_active=True)

    return render(request, 'public/pages/catalog/category_detail.html', {
        'category': category,
        'parts': parts[:60],
        'children': children,
    })


@login_required
def part_request_view(request):
    if request.method == 'POST':
        form = PartRequestForm(request.POST, request.FILES)
        if form.is_valid():
            pr = form.save(commit=False)
            pr.user = request.user
            pr.save()
            messages.success(request, _('Your part request has been sent.'))
            return redirect('catalog:part_list')
    else:
        form = PartRequestForm()

    vehicles = request.user.vehicles.all()
    return render(request, 'public/pages/catalog/part_request.html', {
        'form': form,
        'vehicles': vehicles,
    })


# ============ GARAGE MARKETPLACE VIEWS ============

def is_garage_owner(user):
    from accounts.models import User
    return user.is_authenticated and user.role in [
        User.Role.CLIENT, User.Role.ADMIN, User.Role.SUPERUSER
    ] or (user.is_authenticated and user.is_superuser)


def _get_user_garages(user):
    """Return garages owned by the user."""
    return Garage.objects.filter(owner=user)


def _get_user_first_garage(user):
    """Return the first garage owned by the user, or None."""
    return _get_user_garages(user).first()


@user_passes_test(is_garage_owner)
def garage_product_list_view(request):
    """List products for the garage owner."""
    garage = _get_user_first_garage(request.user)
    if not garage:
        messages.warning(request, _('Veuillez d\'abord créer un garage.'))
        return redirect('garages:garage_create')

    products = Part.objects.filter(garage=garage).select_related('category', 'brand')

    status = request.GET.get('status', '')
    if status == 'active':
        products = products.filter(is_active=True)
    elif status == 'inactive':
        products = products.filter(is_active=False)

    paginator = Paginator(products, 20)
    page = request.GET.get('page')
    products_page = paginator.get_page(page)

    return render(request, 'dashboard/pages/garage/products/list.html', {
        'products': products_page,
        'garage': garage,
        'selected_status': status,
    })


@user_passes_test(is_garage_owner)
def garage_product_add_view(request):
    """Add a new product to the garage."""
    garage = _get_user_first_garage(request.user)
    if not garage:
        messages.warning(request, _('Veuillez d\'abord créer un garage.'))
        return redirect('garages:garage_create')

    if request.method == 'POST':
        form = PartForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            part = form.save(commit=False)
            part.seller = request.user
            part.garage = garage
            part.update_stock_status()
            part.save()
            messages.success(request, _('Produit ajouté avec succès.'))
            return redirect('catalog:garage_products')
    else:
        form = PartForm(user=request.user)

    return render(request, 'dashboard/pages/garage/products/form.html', {
        'form': form,
        'garage': garage,
        'action': 'add',
    })


@user_passes_test(is_garage_owner)
def garage_product_edit_view(request, pk):
    """Edit a product in the garage."""
    garage = _get_user_first_garage(request.user)
    if not garage:
        return redirect('garages:garage_create')

    part = get_object_or_404(Part, pk=pk, garage=garage)

    if request.method == 'POST':
        form = PartForm(request.POST, request.FILES, instance=part, user=request.user)
        if form.is_valid():
            part = form.save(commit=False)
            part.garage = garage
            part.update_stock_status()
            part.save()
            messages.success(request, _('Produit mis à jour.'))
            return redirect('catalog:garage_products')
    else:
        form = PartForm(instance=part, user=request.user)

    return render(request, 'dashboard/pages/garage/products/form.html', {
        'form': form,
        'garage': garage,
        'part': part,
        'action': 'edit',
    })


@user_passes_test(is_garage_owner)
def garage_product_delete_view(request, pk):
    """Soft-delete a product."""
    garage = _get_user_first_garage(request.user)
    if not garage:
        return redirect('garages:garage_create')

    part = get_object_or_404(Part, pk=pk, garage=garage)

    if request.method == 'POST':
        part.is_active = False
        part.save(update_fields=['is_active'])
        messages.success(request, _('Produit désactivé.'))
        return redirect('catalog:garage_products')

    return render(request, 'dashboard/pages/garage/products/delete.html', {
        'part': part,
        'garage': garage,
    })


@user_passes_test(is_garage_owner)
def garage_stock_update_view(request, pk):
    """Update product stock."""
    garage = _get_user_first_garage(request.user)
    if not garage:
        return redirect('garages:garage_create')

    part = get_object_or_404(Part, pk=pk, garage=garage)

    if request.method == 'POST':
        try:
            new_stock = int(request.POST.get('stock', part.stock))
            if new_stock < 0:
                messages.error(request, _('Le stock ne peut pas être négatif.'))
            else:
                part.stock = new_stock
                part.save(update_fields=['stock'])
                part.update_stock_status()
                messages.success(request, _('Stock mis à jour.'))
        except (ValueError, TypeError):
            messages.error(request, _('Valeur de stock invalide.'))

    return redirect('catalog:garage_products')


@user_passes_test(is_garage_owner)
def garage_product_toggle_view(request, pk):
    """Toggle product active status."""
    garage = _get_user_first_garage(request.user)
    if not garage:
        return redirect('garages:garage_create')

    part = get_object_or_404(Part, pk=pk, garage=garage)

    if request.method == 'POST':
        part.is_active = not part.is_active
        part.save(update_fields=['is_active'])
        status = _('activé') if part.is_active else _('désactivé')
        messages.success(request, _('Produit %(status)s.') % {'status': status})

    return redirect('catalog:garage_products')
