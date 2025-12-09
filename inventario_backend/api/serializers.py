"""
Serializers for the inventory API.

These map Django models to JSON representations used by the REST API.
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import (
    Alert,
    Category,
    InventoryItem,
    Location,
    Movement,
    Procedure,
    UserProfile,
)

User = get_user_model()


# PUBLIC_INTERFACE
class LocationSerializer(serializers.ModelSerializer):
    """Serializer for Location objects."""

    class Meta:
        model = Location
        fields = [
            "id",
            "name",
            "code",
            "location_type",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# PUBLIC_INTERFACE
class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category objects."""

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# PUBLIC_INTERFACE
class InventoryItemListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing inventory items.

    Designed for fast grids / tables where only summary data is needed.
    """

    category_name = serializers.CharField(source="category.name", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "code",
            "name",
            "status",
            "quantity",
            "min_threshold",
            "category",
            "category_name",
            "location",
            "location_name",
            "owner",
            "owner_username",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# PUBLIC_INTERFACE
class InventoryItemDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for inventory items, including description
    and serial number.
    """

    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        source="category",
        queryset=Category.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    location = LocationSerializer(read_only=True)
    location_id = serializers.PrimaryKeyRelatedField(
        source="location",
        queryset=Location.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "code",
            "name",
            "description",
            "serial_number",
            "status",
            "quantity",
            "min_threshold",
            "category",
            "category_id",
            "location",
            "location_id",
            "owner",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        """
        Validate consistency between quantity and threshold.

        Ensures that quantity is non-negative and threshold is reasonable.
        """
        quantity = attrs.get("quantity", getattr(self.instance, "quantity", 0))
        min_threshold = attrs.get(
            "min_threshold",
            getattr(self.instance, "min_threshold", 0),
        )

        if quantity < 0:
            raise serializers.ValidationError("Quantity cannot be negative.")

        if min_threshold < 0:
            raise serializers.ValidationError("Minimum threshold cannot be negative.")

        return attrs


# PUBLIC_INTERFACE
class MovementSerializer(serializers.ModelSerializer):
    """
    Serializer for Movement objects.

    The service layer will handle the stock/locations update logic; this
    serializer focuses on validating input data.
    """

    item_code = serializers.CharField(source="item.code", read_only=True)

    class Meta:
        model = Movement
        fields = [
            "id",
            "item",
            "item_code",
            "from_location",
            "to_location",
            "movement_type",
            "quantity",
            "performed_by",
            "performed_at",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_performed_at(self, value):
        """Ensure performed_at is not in the far future."""
        if value > timezone.now() + timezone.timedelta(days=1):
            raise serializers.ValidationError(
                "performed_at cannot be more than 1 day in the future.",
            )
        return value

    def validate(self, attrs):
        """
        Ensure that quantity is not zero and movement_type is compatible
        with locations.
        """
        quantity = attrs.get("quantity")
        movement_type = attrs.get("movement_type")
        from_location = attrs.get("from_location")
        to_location = attrs.get("to_location")

        if quantity == 0:
            raise serializers.ValidationError("Quantity cannot be zero.")

        if movement_type == Movement.TYPE_TRANSFER and (not from_location or not to_location):
            raise serializers.ValidationError(
                "Transfer movements require from_location and to_location.",
            )

        return attrs


# PUBLIC_INTERFACE
class ProcedureSerializer(serializers.ModelSerializer):
    """Serializer for Procedure objects."""

    class Meta:
        model = Procedure
        fields = [
            "id",
            "title",
            "slug",
            "content",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# PUBLIC_INTERFACE
class AlertSerializer(serializers.ModelSerializer):
    """Serializer for Alert objects."""

    item_code = serializers.CharField(source="item.code", read_only=True)

    class Meta:
        model = Alert
        fields = [
            "id",
            "item",
            "item_code",
            "level",
            "message",
            "is_active",
            "is_auto",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "is_auto"]


# PUBLIC_INTERFACE
class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for the UserProfile model.

    Exposes the role field used for role-based access control.
    """

    class Meta:
        model = UserProfile
        fields = ["role"]


# PUBLIC_INTERFACE
class UserSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for the Django user including inventory profile role.

    Used primarily by the /auth/me endpoint.
    """

    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "is_staff",
            "is_superuser",
            "profile",
        ]
        read_only_fields = [
            "id",
            "is_active",
            "is_staff",
            "is_superuser",
            "profile",
        ]


# PUBLIC_INTERFACE
class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for registering a new user together with an inventory role.

    This is used by the /api/auth/register endpoint and is restricted
    to admin/manager users.
    """

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text="Password for the new user (not returned in responses).",
    )
    role = serializers.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        write_only=True,
        help_text="Inventory role for the new user.",
    )
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "password",
            "role",
            "profile",
        ]
        read_only_fields = ["id", "profile"]

    def create(self, validated_data):
        """
        Create a new user and associated UserProfile with the provided role.
        """
        role = validated_data.pop("role")
        password = validated_data.pop("password")

        user = User.objects.create_user(**validated_data, password=password)
        UserProfile.objects.create(user=user, role=role)

        return user
