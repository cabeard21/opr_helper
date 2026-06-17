from django.contrib import admin

from lists.models import ArmyList, ListUnit


@admin.register(ArmyList)
class ArmyListAdmin(admin.ModelAdmin):
    list_display = ("name", "faction", "point_limit", "updated_at")
    list_filter = ("faction",)
    search_fields = ("name", "faction__name")


@admin.register(ListUnit)
class ListUnitAdmin(admin.ModelAdmin):
    list_display = ("army_list", "unit", "model_count", "selected_weapon_slot")
    list_filter = ("army_list__faction",)
    search_fields = ("army_list__name", "unit__name")
