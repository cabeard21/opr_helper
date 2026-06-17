from django.contrib import admin

from army_books.models import Faction, Unit, UnitWeaponSlot, Weapon


@admin.register(Faction)
class FactionAdmin(admin.ModelAdmin):
    list_display = ("name", "version", "last_fetched", "source_slug")
    search_fields = ("name", "source_uid", "source_slug")


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("name", "faction", "quality", "defense", "tough", "points")
    list_filter = ("faction", "quality", "defense")
    search_fields = ("name", "source_uid", "faction__name")


@admin.register(Weapon)
class WeaponAdmin(admin.ModelAdmin):
    list_display = ("name", "range", "attacks_string", "attacks", "ap")
    list_filter = ("range", "ap")
    search_fields = ("name", "source_uid")


@admin.register(UnitWeaponSlot)
class UnitWeaponSlotAdmin(admin.ModelAdmin):
    list_display = ("unit", "weapon", "is_default", "upgrade_cost")
    list_filter = ("is_default", "unit__faction")
    search_fields = ("unit__name", "weapon__name")
