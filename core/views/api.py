from django.http import JsonResponse
from django.views.decorators.http import require_GET

from core.models import Neighborhood


@require_GET
def neighborhoods_api(request, city_id):
    """API: retourne les quartiers d'une ville donnée."""
    neighborhoods = Neighborhood.objects.filter(
        city_id=city_id, is_active=True
    ).order_by('name').values('id', 'name', 'slug')
    return JsonResponse(list(neighborhoods), safe=False)
