"""
Service layer for the inventory domain.

This module centralizes business rules for movements, stock updates, and
automatic alert generation so viewsets can remain thin.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.utils import timezone

from .models import Alert, InventoryItem, Location, Movement


@dataclass
class MovementResult:
    """
    Simple value object summarizing the outcome of a movement operation.
    """

    movement: Movement
    item: InventoryItem
    created_alert: Optional[Alert]


# PUBLIC_INTERFACE
def is_below_minimum_stock(item: InventoryItem) -> bool:
    """
    Check if the given item's quantity is below its configured minimum threshold.

    Returns True when an alert should be generated, False otherwise.
    """
    return item.min_threshold > 0 and item.quantity < item.min_threshold


# PUBLIC_INTERFACE
@transaction.atomic
def register_movement(
    *,
    item: InventoryItem,
    from_location: Optional[Location],
    to_location: Optional[Location],
    movement_type: str,
    quantity: int,
    performed_by,
    performed_at,
    notes: str = "",
) -> MovementResult:
    """
    Create a Movement record and update the related InventoryItem accordingly.

    This function:
    - creates a Movement with the provided details
    - updates the item's quantity and location depending on movement_type
    - generates or closes stock alerts when thresholds are crossed
    """
    # Persist movement record first
    movement = Movement.objects.create(
        item=item,
        from_location=from_location,
        to_location=to_location,
        movement_type=movement_type,
        quantity=quantity,
        performed_by=performed_by,
        performed_at=performed_at,
        notes=notes,
    )

    # Business rules for stock/locations
    if movement_type == Movement.TYPE_INBOUND:
        item.quantity = max(0, item.quantity + quantity)
        if to_location:
            item.location = to_location
    elif movement_type == Movement.TYPE_OUTBOUND:
        item.quantity = max(0, item.quantity - abs(quantity))
        if to_location:
            item.location = to_location
    elif movement_type == Movement.TYPE_TRANSFER:
        if to_location:
            item.location = to_location
    elif movement_type == Movement.TYPE_ADJUSTMENT:
        item.quantity = max(0, item.quantity + quantity)

    item.save(update_fields=["quantity", "location", "updated_at"])

    created_alert: Optional[Alert] = None

    # Automatic stock alerts
    if is_below_minimum_stock(item):
        created_alert = Alert.objects.create(
            item=item,
            level=Alert.LEVEL_WARNING,
            message=f"Stock por debajo del mínimo para {item.code} ({item.name}).",
            is_auto=True,
            is_active=True,
        )
    else:
        # Resolve any previous auto stock alerts for this item
        now = timezone.now()
        Alert.objects.filter(
            item=item,
            is_auto=True,
            is_active=True,
        ).update(is_active=False, resolved_at=now)

    return MovementResult(movement=movement, item=item, created_alert=created_alert)
