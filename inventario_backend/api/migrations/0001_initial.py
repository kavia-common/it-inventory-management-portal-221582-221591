"""
Initial migration for the inventory domain models.
"""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """
    Create the core inventory tables:
    - Location
    - Category
    - InventoryItem
    - Movement
    - Procedure
    - Alert
    """

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Location",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=255)),
                ("code", models.CharField(max_length=64, unique=True)),
                (
                    "location_type",
                    models.CharField(
                        choices=[
                            ("ISLAND", "Isla"),
                            ("CABINET", "Armario"),
                            ("HOME", "Casa"),
                            ("WAREHOUSE", "Almacén"),
                            ("OTHER", "Otro"),
                        ],
                        default="OTHER",
                        max_length=16,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "ordering": ["name"],
                "verbose_name": "Location",
                "verbose_name_plural": "Locations",
            },
        ),
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=255, unique=True)),
                ("description", models.TextField(blank=True)),
            ],
            options={
                "ordering": ["name"],
                "verbose_name": "Category",
                "verbose_name_plural": "Categories",
            },
        ),
        migrations.CreateModel(
            name="InventoryItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "code",
                    models.CharField(
                        help_text="Código único del elemento (por ejemplo, código interno o de hoja Excel).",
                        max_length=64,
                        unique=True,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("serial_number", models.CharField(blank=True, help_text="Número de serie si aplica.", max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("IN_STOCK", "En stock"),
                            ("ASSIGNED", "Asignado"),
                            ("IN_REPAIR", "En reparación"),
                            ("LOST", "Perdido"),
                            ("RETIRED", "Retirado"),
                        ],
                        default="IN_STOCK",
                        max_length=16,
                    ),
                ),
                ("quantity", models.PositiveIntegerField(default=1, help_text="Cantidad de unidades representadas por este registro.")),
                ("min_threshold", models.PositiveIntegerField(default=0, help_text="Cantidad mínima recomendada para alertas de stock.")),
                ("is_active", models.BooleanField(default=True, help_text="Indica si el elemento sigue siendo relevante para el inventario.")),
                (
                    "category",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="items",
                        to="api.category",
                    ),
                ),
                (
                    "location",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="items",
                        to="api.location",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        help_text="Usuario actual responsable del equipo, si aplica.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="owned_items",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["name", "code"],
                "verbose_name": "Inventory item",
                "verbose_name_plural": "Inventory items",
            },
        ),
        migrations.CreateModel(
            name="Procedure",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=255)),
                ("slug", models.SlugField(max_length=255, unique=True)),
                ("content", models.TextField(help_text="Contenido en texto plano o Markdown.")),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "ordering": ["title"],
                "verbose_name": "Procedure",
                "verbose_name_plural": "Procedures",
            },
        ),
        migrations.CreateModel(
            name="Alert",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "level",
                    models.CharField(
                        choices=[
                            ("INFO", "Info"),
                            ("WARNING", "Aviso"),
                            ("CRITICAL", "Crítica"),
                        ],
                        default="INFO",
                        max_length=16,
                    ),
                ),
                ("message", models.CharField(max_length=512)),
                ("is_active", models.BooleanField(default=True, help_text="Si la alerta sigue vigente.")),
                ("is_auto", models.BooleanField(default=True, help_text="Indica si la alerta fue generada automáticamente por el sistema.")),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                (
                    "item",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="alerts",
                        to="api.inventoryitem",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "verbose_name": "Alert",
                "verbose_name_plural": "Alerts",
            },
        ),
        migrations.CreateModel(
            name="Movement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "movement_type",
                    models.CharField(
                        choices=[
                            ("INBOUND", "Ingreso"),
                            ("OUTBOUND", "Salida"),
                            ("TRANSFER", "Transferencia"),
                            ("ADJUSTMENT", "Ajuste"),
                        ],
                        max_length=16,
                    ),
                ),
                ("quantity", models.IntegerField(help_text="Cantidad movida (puede ser negativa en ajustes).")),
                ("performed_at", models.DateTimeField(help_text="Fecha/hora efectiva del movimiento.")),
                ("notes", models.TextField(blank=True)),
                (
                    "from_location",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="movements_from",
                        to="api.location",
                    ),
                ),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="movements",
                        to="api.inventoryitem",
                    ),
                ),
                (
                    "performed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="movements_performed",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "to_location",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="movements_to",
                        to="api.location",
                    ),
                ),
            ],
            options={
                "ordering": ["-performed_at", "-created_at"],
                "verbose_name": "Movement",
                "verbose_name_plural": "Movements",
            },
        ),
    ]
