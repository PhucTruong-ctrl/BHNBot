"""UI Layer for Fishing Cog - All Discord Views and Modals."""

from .sell_views import FishSellView, HagglingView, TrashSellView, InteractiveSellEventView
from .tournament_views import TournamentLobbyView
from .event_views import MeteorWishView, GenericActionView
from .npc_views import InteractiveNPCView
from .legendary_views import LegendaryBossFightView, LegendaryHallView
from .collection_views import FishingCollectionView

__all__ = [
    "FishSellView",
    "HagglingView",
    "TrashSellView",
    "InteractiveSellEventView",
    "TournamentLobbyView",
    "MeteorWishView",
    "GenericActionView",
    "InteractiveNPCView",
    "LegendaryBossFightView",
    "LegendaryHallView",
    "FishingCollectionView",
]
