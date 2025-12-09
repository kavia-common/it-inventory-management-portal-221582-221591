"""
Custom permission classes for the inventory API, including role-based access.

This module defines:

- IsInventoryAdminOrReadOnly: write access limited to inventory admins.
- IsInventoryAdmin: strict admin-only access.
- IsAdminOrManagerRole: access for users with admin/manager profile roles.
- Helper utilities for checking user roles.
"""

from typing import Any, Iterable

from django.contrib.auth.models import Group
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.request import Request
from rest_framework.views import View

from .models import UserProfile


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


# PUBLIC_INTERFACE
def user_has_any_role(user, roles: Iterable[str]) -> bool:
    """
    Check whether a user has any of the given inventory roles.

    The function returns True when:
    - the user is superuser or staff, OR
    - the user's profile role is contained in the roles iterable.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False

    if user.is_superuser or user.is_staff:
        return True

    try:
        profile: UserProfile = user.profile  # type: ignore[assignment]
    except UserProfile.DoesNotExist:
        return False
    except AttributeError:
        # Profile relation not present on the user model
        return False

    return profile.role in set(roles)


# PUBLIC_INTERFACE
class IsAdminOrManagerRole(BasePermission):
    """
    Permission that grants access only to users with admin or manager roles.

    A user is considered allowed when:
    - they are staff or superuser, OR
    - their UserProfile.role is 'admin' or 'manager'.
    """

    message = "Only admin or manager users can access this endpoint."

    def has_permission(self, request: Request, view: View) -> bool:
        """Return True if the requesting user is admin/manager according to profile."""
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser:
            return True

        return user_has_any_role(
            user,
            roles=[UserProfile.ROLE_ADMIN, UserProfile.ROLE_MANAGER],
        )
