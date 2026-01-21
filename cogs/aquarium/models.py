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
    theme_url = fields.TextField(null=True, default=None)
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
    item_id = fields.CharField(max_length=50, null=True)
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

class Loadout(models.Model):
    """
    Represents a saved loadout configuration for a specific activity.
    Users can save multiple loadouts and switch between them.
    """
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField('models.UserAquarium', related_name='loadouts', to_field='user_id')
    name = fields.CharField(max_length=50)
    activity = fields.CharField(max_length=20)  # fishing, harvest, sell, passive, global, quest, relationship, gambling
    slot_0 = fields.CharField(max_length=50, null=True)
    slot_1 = fields.CharField(max_length=50, null=True)
    slot_2 = fields.CharField(max_length=50, null=True)
    slot_3 = fields.CharField(max_length=50, null=True)
    slot_4 = fields.CharField(max_length=50, null=True)
    is_active = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "loadouts"
        unique_together = (("user", "name"),)


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
    total_vip_days = fields.IntField(default=0)
    total_spent = fields.BigIntField(default=0)

    class Meta:
        table = "vip_subscriptions"
