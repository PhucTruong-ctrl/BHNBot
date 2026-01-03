from tortoise import fields, models

class UserAquarium(models.Model):
    """
    Extension of the User profile for Aquarium stats.
    Linked to the main Discord User ID.
    PROS: Separates Aquarium bloat from core User table.
    """
    user_id = fields.BigIntField(pk=True)
    leaf_coin = fields.BigIntField(default=0)
    charm_point = fields.IntField(default=0)
    home_thread_id = fields.BigIntField(null=True)
    dashboard_message_id = fields.BigIntField(null=True)
    
    # Meta info
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_aquarium"

class HomeSlot(models.Model):
    """
    Represents an item placed in a specific slot in the user's home.
    Composite Key logic handled by Unique Together.
    """
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField('models.UserAquarium', related_name='slots', to_field='user_id')
    slot_index = fields.IntField() # 0-4 usually
    item_id = fields.CharField(max_length=50, null=True) # Key from constants.DECOR_ITEMS
    placed_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "home_slots"
        unique_together = (("user", "slot_index"),)

class UserDecor(models.Model):
    """
    Inventory for Decor items (separate from Fishing inventory).
    """
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField('models.UserAquarium', related_name='decor', to_field='user_id')
    item_id = fields.CharField(max_length=50)
    quantity = fields.IntField(default=0)
    
    class Meta:
        table = "user_decor"
        unique_together = (("user", "item_id"),)

class HomeVisit(models.Model):
    """
    Tracks social visits to prevent spam/abuse.
    """
    id = fields.IntField(pk=True)
    visitor_id = fields.BigIntField() # Not enforcing FK to avoid circular dependencies if simple
    host = fields.ForeignKeyField('models.UserAquarium', related_name='visits_received', to_field='user_id')
    visited_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "home_visits"
        # index on (visitor_id, visited_at) created automatically or via manual SQL if needed

class VIPSubscription(models.Model):
    """
    VIP System subscriptions.
    """
    user_id = fields.BigIntField(pk=True)
    tier_level = fields.IntField() # 1=Silver, 2=Gold, 3=Diamond
    start_date = fields.DatetimeField(auto_now_add=True)
    expiry_date = fields.DatetimeField()
    custom_footer = fields.TextField(null=True)
    auto_renew = fields.BooleanField(default=False)

    class Meta:
        table = "vip_subscriptions"
