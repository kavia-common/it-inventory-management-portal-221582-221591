"""
Database models for the api app.

This module defines the core inventory domain models used by the backend:
locations, categories, inventory items, movements, procedures, and alerts.
"""

from django.conf import settings
from django.db import models


# PUBLIC_INTERFACE
class TimestampedModel(models.Model):
    """
    Abstract base model that adds created/updated timestamps.

    Can be extended by concrete inventory-related models in this app.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# PUBLIC_INTERFACE
class Location(TimestampedModel):
    """
    Physical or logical place where inventory can reside,
    such as islas, armarios, casa, or other locations.
    """

    TYPE_ISLAND = "ISLAND"
    TYPE_CABINET = "CABINET"
    TYPE_HOME = "HOME"
    TYPE_WAREHOUSE = "WAREHOUSE"
    TYPE_OTHER = "OTHER"

    LOCATION_TYPE_CHOICES = [
        (TYPE_ISLAND, "Isla"),
        (TYPE_CABINET, "Armario"),
        (TYPE_HOME, "Casa"),
        (TYPE_WAREHOUSE, "Almacén"),
        (TYPE_OTHER, "Otro"),
    ]

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=64, unique=True)
    location_type = models.CharField(
        max_length=16,
        choices=LOCATION_TYPE_CHOICES,
        default=TYPE_OTHER,
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Location"
        verbose_name_plural = "Locations"

    def __str__(self) -> str:
        """Return a human-readable representation for admin and debugging."""
        return f"{self.name} ({self.code})"


# PUBLIC_INTERFACE
class Category(TimestampedModel):
    """
    Category or family for inventory items (e.g., portátiles, monitores).
    """

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self) -> str:
        """Return a human-readable representation for admin and debugging."""
        return self.name


# PUBLIC_INTERFACE
class InventoryItem(TimestampedModel):
    """
    An individual or grouped inventory element, optionally with quantity.

    This represents the 'general inventory' entries and supports:
    - status tracking (in stock, assigned, in repair, etc.)
    - minimal stock thresholds
    - association with a location and an optional owner user
    """

    STATUS_IN_STOCK = "IN_STOCK"
    STATUS_ASSIGNED = "ASSIGNED"
    STATUS_IN_REPAIR = "IN_REPAIR"
    STATUS_LOST = "LOST"
    STATUS_RETIRED = "RETIRED"

    STATUS_CHOICES = [
        (STATUS_IN_STOCK, "En stock"),
        (STATUS_ASSIGNED, "Asignado"),
        (STATUS_IN_REPAIR, "En reparación"),
        (STATUS_LOST, "Perdido"),
        (STATUS_RETIRED, "Retirado"),
    ]

    code = models.CharField(
        max_length=64,
        unique=True,
        help_text="Código único del elemento (por ejemplo, código interno o de hoja Excel).",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="items",
        null=True,
        blank=True,
    )
    serial_number = models.CharField(
        max_length=255,
        blank=True,
        help_text="Número de serie si aplica.",
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_IN_STOCK,
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="items",
        null=True,
        blank=True,
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="owned_items",
        null=True,
        blank=True,
        help_text="Usuario actual responsable del equipo, si aplica.",
    )
    quantity = models.PositiveIntegerField(
        default=1,
        help_text="Cantidad de unidades representadas por este registro.",
    )
    min_threshold = models.PositiveIntegerField(
        default=0,
        help_text="Cantidad mínima recomendada para alertas de stock.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Indica si el elemento sigue siendo relevante para el inventario.",
    )

    class Meta:
        ordering = ["name", "code"]
        verbose_name = "Inventory item"
        verbose_name_plural = "Inventory items"

    def __str__(self) -> str:
        """Return a human-readable representation for admin and debugging."""
        return f"{self.code} - {self.name}"


# PUBLIC_INTERFACE
class Movement(TimestampedModel):
    """
    Record of a movement or change affecting an inventory item.

    This supports:
    - ingreso / salida / transferencia / ajustes de stock
    - histórico de ubicaciones
    - enlace con la persona que realiza el movimiento
    """

    TYPE_INBOUND = "INBOUND"
    TYPE_OUTBOUND = "OUTBOUND"
    TYPE_TRANSFER = "TRANSFER"
    TYPE_ADJUSTMENT = "ADJUSTMENT"

    MOVEMENT_TYPE_CHOICES = [
        (TYPE_INBOUND, "Ingreso"),
        (TYPE_OUTBOUND, "Salida"),
        (TYPE_TRANSFER, "Transferencia"),
        (TYPE_ADJUSTMENT, "Ajuste"),
    ]

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="movements",
    )
    from_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        related_name="movements_from",
        null=True,
        blank=True,
    )
    to_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        related_name="movements_to",
        null=True,
        blank=True,
    )
    movement_type = models.CharField(
        max_length=16,
        choices=MOVEMENT_TYPE_CHOICES,
    )
    quantity = models.IntegerField(
        help_text="Cantidad movida (puede ser negativa en ajustes).",
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="movements_performed",
        null=True,
        blank=True,
    )
    performed_at = models.DateTimeField(
        help_text="Fecha/hora efectiva del movimiento.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-performed_at", "-created_at"]
        verbose_name = "Movement"
        verbose_name_plural = "Movements"

    def __str__(self) -> str:
        """Return a human-readable representation for admin and debugging."""
        return f"{self.movement_type} {self.quantity} x {self.item.code}"


# PUBLIC_INTERFACE
class Procedure(TimestampedModel):
    """
    Documented procedure or checklist related to inventory operations.

    These map to the 'procedimientos' section of the portal.
    """

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    content = models.TextField(help_text="Contenido en texto plano o Markdown.")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]
        verbose_name = "Procedure"
        verbose_name_plural = "Procedures"

    def __str__(self) -> str:
        """Return a human-readable representation for admin and debugging."""
        return self.title


# PUBLIC_INTERFACE
class Alert(TimestampedModel):
    """
    Alert linked to an inventory item or inventory process.

    Typical use cases:
    - stock por debajo del mínimo
    - incidencias de movimiento
    - fechas de revisión o mantenimiento
    """

    LEVEL_INFO = "INFO"
    LEVEL_WARNING = "WARNING"
    LEVEL_CRITICAL = "CRITICAL"

    LEVEL_CHOICES = [
        (LEVEL_INFO, "Info"),
        (LEVEL_WARNING, "Aviso"),
        (LEVEL_CRITICAL, "Crítica"),
    ]

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name="alerts",
        null=True,
        blank=True,
    )
    level = models.CharField(
        max_length=16,
        choices=LEVEL_CHOICES,
        default=LEVEL_INFO,
    )
    message = models.CharField(max_length=512)
    is_active = models.BooleanField(
        default=True,
        help_text="Si la alerta sigue vigente.",
    )
    is_auto = models.BooleanField(
        default=True,
        help_text="Indica si la alerta fue generada automáticamente por el sistema.",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Alert"
        verbose_name_plural = "Alerts"

    def __str__(self) -> str:
        """Return a human-readable representation for admin and debugging."""
        return f"[{self.level}] {self.message}"
