"""
Django admin module for the api app.

This registers the inventory-related models so they can be managed
from the Django admin interface.
"""

from django.contrib import admin

from .models import (
    Alert,
    Category,
    InventoryItem,
    Location,
    Movement,
    Procedure,
)


# PUBLIC_INTERFACE
@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    """Admin configuration for Location entries."""

    list_display = ("name", "code", "location_type", "is_active", "created_at")
    list_filter = ("location_type", "is_active")
    search_fields = ("name", "code", "description")


# PUBLIC_INTERFACE
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin configuration for Category entries."""

    list_display = ("name", "created_at")
    search_fields = ("name",)


# PUBLIC_INTERFACE
@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    """Admin configuration for InventoryItem entries."""

    list_display = (
        "code",
        "name",
        "status",
        "location",
        "owner",
        "quantity",
        "min_threshold",
        "is_active",
    )
    list_filter = ("status", "is_active", "category", "location")
    search_fields = ("code", "name", "serial_number", "description")
    autocomplete_fields = ("category", "location", "owner")


# PUBLIC_INTERFACE
@admin.register(Movement)
class MovementAdmin(admin.ModelAdmin):
    """Admin configuration for Movement entries."""

    list_display = (
        "item",
        "movement_type",
        "quantity",
        "from_location",
        "to_location",
        "performed_by",
        "performed_at",
    )
    list_filter = ("movement_type", "from_location", "to_location")
    search_fields = ("item__code", "item__name", "notes")
    autocomplete_fields = ("item", "from_location", "to_location", "performed_by")


# PUBLIC_INTERFACE
@admin.register(Procedure)
class ProcedureAdmin(admin.ModelAdmin):
    """Admin configuration for Procedure entries."""

    list_display = ("title", "slug", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("title", "slug", "content")
    prepopulated_fields = {"slug": ("title",)}


# PUBLIC_INTERFACE
@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    """Admin configuration for Alert entries."""

    list_display = ("level", "message", "item", "is_active", "is_auto", "created_at")
    list_filter = ("level", "is_active", "is_auto")
    search_fields = ("message", "item__code", "item__name")
    autocomplete_fields = ("item",)
