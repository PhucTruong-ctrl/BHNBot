from .trash_sell_view import TrashSellView
from .event_views import MeteorWishView

# Registry Mapping
# Key: String ID from JSON config
# Value: View Class
VIEW_REGISTRY = {
    "TrashSellView": TrashSellView,
    "MeteorWishView": MeteorWishView
}

def get_view_class(view_name: str):
    """Retrieves a View class from the registry by name.
    
    Args:
        view_name (str): The name of the view class (e.g. "TrashSellView")
        
    Returns:
        class: The View class, or None if not found.
    """
    return VIEW_REGISTRY.get(view_name)
