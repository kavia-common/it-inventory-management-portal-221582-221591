"""
Management command to seed minimal initial data for the inventory system.

This command is safe to run multiple times; it is idempotent and will:
- Ensure an initial admin user exists (with an associated UserProfile role).
- Ensure at least one sample Location exists.
- Ensure at least one sample Category exists.
- Ensure one sample InventoryItem exists, linked to the sample Location/Category.

Environment variables
---------------------
To control the default admin that will be created, you can define:

- INITIAL_ADMIN_USERNAME  (default: "admin")
- INITIAL_ADMIN_EMAIL     (default: "admin@example.com")
- INITIAL_ADMIN_PASSWORD  (default: "admin123" - development only, change in real envs)

IMPORTANT:
    For production or shared environments, override these values via a .env file
    or environment variables managed outside of the codebase. Do not commit any
    real secrets.
"""

from __future__ import annotations

import os
from typing import Tuple

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import (
    Category,
    InventoryItem,
    Location,
    UserProfile,
)


User = get_user_model()


def _get_admin_credentials() -> Tuple[str, str, str]:
    """
    Read admin seed credentials from environment with sensible defaults.

    Returns:
        A tuple (username, email, password).
    """
    username = os.environ.get("INITIAL_ADMIN_USERNAME", "admin")
    email = os.environ.get("INITIAL_ADMIN_EMAIL", "admin@example.com")
    password = os.environ.get("INITIAL_ADMIN_PASSWORD", "admin123")
    return username, email, password


def _ensure_admin_user() -> User:
    """
    Ensure there is at least one admin user with an associated UserProfile.

    The created/updated user will have:
    - is_staff=True
    - is_superuser=True
    - profile.role='admin'

    Returns:
        The ensured User instance.
    """
    username, email, password = _get_admin_credentials()

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": email,
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
        },
    )

    if created:
        user.set_password(password)
        user.save(update_fields=["password", "email", "is_staff", "is_superuser", "is_active"])
    else:
        # Ensure flags remain aligned with "admin" expectations
        update_fields = []
        if not user.is_staff:
            user.is_staff = True
            update_fields.append("is_staff")
        if not user.is_superuser:
            user.is_superuser = True
            update_fields.append("is_superuser")
        if not user.is_active:
            user.is_active = True
            update_fields.append("is_active")
        if email and user.email != email:
            user.email = email
            update_fields.append("email")
        if update_fields:
            user.save(update_fields=update_fields)

    # Ensure profile with admin role
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"role": UserProfile.ROLE_ADMIN},
    )
    if profile.role != UserProfile.ROLE_ADMIN:
        profile.role = UserProfile.ROLE_ADMIN
        profile.save(update_fields=["role"])

    return user


def _ensure_sample_location() -> Location:
    """
    Ensure a sample Location exists for E2E validation.

    Returns:
        The ensured Location instance.
    """
    location, _ = Location.objects.get_or_create(
        code="ISLA-001",
        defaults={
            "name": "Isla principal",
            "location_type": Location.TYPE_ISLAND,
            "description": "Ubicación de ejemplo para validar E2E.",
            "is_active": True,
        },
    )
    return location


def _ensure_sample_category() -> Category:
    """
    Ensure a sample Category exists for E2E validation.

    Returns:
        The ensured Category instance.
    """
    category, _ = Category.objects.get_or_create(
        name="Portátiles",
        defaults={
            "description": "Categoría de ejemplo para equipos portátiles.",
        },
    )
    return category


def _ensure_sample_item(
    *,
    location: Location,
    category: Category,
    owner: User | None,
) -> InventoryItem:
    """
    Ensure a sample InventoryItem exists and is linked to the given relations.

    Args:
        location: Location to associate with the item.
        category: Category to associate with the item.
        owner: Optional owner user (admin by default).

    Returns:
        The ensured InventoryItem instance.
    """
    item, created = InventoryItem.objects.get_or_create(
        code="IT-DEMO-001",
        defaults={
            "name": "Portátil de ejemplo",
            "description": "Elemento de inventario de ejemplo para pruebas E2E.",
            "status": InventoryItem.STATUS_IN_STOCK,
            "location": location,
            "category": category,
            "owner": owner,
            "quantity": 5,
            "min_threshold": 2,
            "is_active": True,
        },
    )

    if not created:
        # Keep demo data roughly aligned if the item already exists
        changed = False
        if item.location_id != location.id:
            item.location = location
            changed = True
        if item.category_id != category.id:
            item.category = category
            changed = True
        if owner and item.owner_id != owner.id:
            item.owner = owner
            changed = True
        if changed:
            item.save(update_fields=["location", "category", "owner", "updated_at"])

    return item


# PUBLIC_INTERFACE
class Command(BaseCommand):
    """
    PUBLIC_INTERFACE: Seed minimal initial data for local development and E2E checks.

    This command can be invoked as:

        python manage.py seed_initial_data

    It is safe to run multiple times. Typical usage:

    1. Ensure PostgreSQL is running and Django can connect (see README).
    2. Apply migrations:

           python manage.py migrate

    3. Seed initial data:

           python manage.py seed_initial_data

    4. Log in from the frontend using the seeded admin credentials and
       verify that:
       - At least one location exists.
       - At least one category exists.
       - The sample inventory item appears in the inventory views.
    """

    help = "Seed minimal initial data: admin user, sample Location/Category, and InventoryItem."

    @transaction.atomic
    def handle(self, *args, **options):
        """Entry point for the management command."""
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding initial inventory data..."))

        admin_user = _ensure_admin_user()
        self.stdout.write(self.style.SUCCESS(f"Admin user ensured: {admin_user.username} (id={admin_user.id})"))

        location = _ensure_sample_location()
        self.stdout.write(self.style.SUCCESS(f"Sample Location ensured: {location} (id={location.id})"))

        category = _ensure_sample_category()
        self.stdout.write(self.style.SUCCESS(f"Sample Category ensured: {category.name} (id={category.id})"))

        item = _ensure_sample_item(location=location, category=category, owner=admin_user)
        self.stdout.write(
            self.style.SUCCESS(
                f"Sample InventoryItem ensured: {item.code} - {item.name} (id={item.id})",
            ),
        )

        self.stdout.write(self.style.MIGRATE_HEADING("Seed completed successfully."))
        self.stdout.write(
            "You can now log in from the frontend using the seeded admin credentials\n"
            "and verify that the sample inventory data is visible through the API.",
        )
