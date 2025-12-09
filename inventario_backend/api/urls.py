"""
URL configuration for the inventory API.

This module wires up:
- /api/health/  -> health check endpoint
- /api/locations/
- /api/categories/
- /api/items/
- /api/movements/
- /api/procedures/
- /api/alerts/
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AlertViewSet,
    CategoryViewSet,
    InventoryItemViewSet,
    LocationViewSet,
    MovementViewSet,
    ProcedureViewSet,
    health,
)

router = DefaultRouter()
router.register(r"locations", LocationViewSet, basename="location")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"items", InventoryItemViewSet, basename="item")
router.register(r"movements", MovementViewSet, basename="movement")
router.register(r"procedures", ProcedureViewSet, basename="procedure")
router.register(r"alerts", AlertViewSet, basename="alert")

urlpatterns = [
    path("health/", health, name="Health"),
    path("", include(router.urls)),
]
