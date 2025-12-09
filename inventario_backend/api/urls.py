"""
URL configuration for the inventory API.

This module wires up:
- /api/health/              -> health check endpoint
- /api/locations/
- /api/categories/
- /api/items/
- /api/movements/
- /api/procedures/
- /api/alerts/
- /api/auth/login           -> JWT access/refresh token obtain
- /api/auth/refresh         -> JWT refresh
- /api/auth/register        -> Create new users with roles (admin/manager only)
- /api/auth/me              -> Get current user profile and role
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    AlertViewSet,
    CategoryViewSet,
    InventoryItemViewSet,
    LocationViewSet,
    MeView,
    MovementViewSet,
    ProcedureViewSet,
    RegisterUserView,
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
    # Authentication / user endpoints
    path("auth/login/", TokenObtainPairView.as_view(), name="auth_login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth_refresh"),
    path("auth/register/", RegisterUserView.as_view(), name="auth_register"),
    path("auth/me/", MeView.as_view(), name="auth_me"),
    # Core inventory API endpoints
    path("", include(router.urls)),
]
