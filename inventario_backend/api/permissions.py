"""
Custom permission classes for the inventory API.
"""

from typing import Any

from django.contrib.auth.models import Group
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.request import Request
from rest_framework.views import View


# PUBLIC_INTERFACE
class IsInventoryAdminOrReadOnly(BasePermission):
    """
    Allow read-only access to authenticated users, but restrict write operations
    to inventory administrators.

    Inventory admin is defined as:
    - a user that is staff/superuser, OR
    - a user that belongs to the "inventory_admins" group.
    """

    message = "You do not have permission to modify inventory data."

    def has_permission(self, request: Request, view: View) -> bool:
        """
        Determine if the incoming request has permission to access the view.

        Read operations (GET, HEAD, OPTIONS) are allowed for authenticated users.
        Write operations are allowed only for inventory admins.
        """
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        if user.is_staff or user.is_superuser:
            return True

        try:
            inventory_admins: Group | None = Group.objects.filter(
                name="inventory_admins",
            ).first()
        except Exception:
            # If groups table is not yet migrated or available, fall back
            # to staff/superuser only.
            inventory_admins = None

        if inventory_admins and inventory_admins in user.groups.all():
            return True

        return False


# PUBLIC_INTERFACE
class IsInventoryAdmin(BasePermission):
    """
    Strict permission only for inventory admins.

    This is used for endpoints that should not be visible to normal users,
    such as configuration or bulk operations.
    """

    message = "Only inventory administrators can access this endpoint."

    def has_permission(self, request: Request, view: View) -> bool:
        """
        Determine if the requesting user is an inventory admin.
        """
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser:
            return True

        try:
            inventory_admins: Any = Group.objects.filter(name="inventory_admins").first()
        except Exception:
            inventory_admins = None

        if inventory_admins and inventory_admins in user.groups.all():
            return True

        return False
