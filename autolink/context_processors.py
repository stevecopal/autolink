"""
Context processors for AutoLink.
"""


def cart_count(request):
    """
    Ajoute le nombre d'articles du panier au contexte de tous les templates.
    """
    count = 0
    try:
        user = getattr(request, 'user', None)
        if user and user.is_authenticated and hasattr(user, 'cart'):
            count = user.cart.item_count
    except Exception:
        pass
    return {'cart_item_count': count}
