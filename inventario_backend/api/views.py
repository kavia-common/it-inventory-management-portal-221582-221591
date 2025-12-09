"""
API views for the inventory backend.

This module exposes:
- a simple health check endpoint
- viewsets for locations, categories, inventory items, movements,
  procedures, and alerts.
- authentication-related endpoints for user registration and profile
  inspection (role-based access built on JWT).
"""

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Alert, Category, InventoryItem, Location, Movement, Procedure
from .permissions import (
    IsAdminOrManagerRole,
    IsInventoryAdmin,
    IsInventoryAdminOrReadOnly,
)
from .serializers import (
    AlertSerializer,
    CategorySerializer,
    InventoryItemDetailSerializer,
    InventoryItemListSerializer,
    LocationSerializer,
    MovementSerializer,
    ProcedureSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)
from .services import register_movement

User = get_user_model()


@api_view(["GET"])
def health(request):
    """
    Lightweight health check endpoint.

    Returns:
        200 OK with a simple JSON payload indicating the server is running.
    """
    return Response({"message": "Server is up!"})


# PUBLIC_INTERFACE
class LocationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing inventory locations such as islas, armarios y casa.

    list:
        Retrieve a list of locations.

    retrieve:
        Retrieve a single location by ID.

    create:
        Create a new location (inventory admin only).

    update/partial_update:
        Modify an existing location (inventory admin only).

    destroy:
        Delete a location (inventory admin only, subject to FK constraints).
    """

    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [IsInventoryAdminOrReadOnly]

    def get_queryset(self):
        """
        Optionally filter locations by 'is_active' query parameter.
        """
        qs = super().get_queryset()
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() in {"1", "true", "yes"}:
                qs = qs.filter(is_active=True)
            elif is_active.lower() in {"0", "false", "no"}:
                qs = qs.filter(is_active=False)
        return qs


# PUBLIC_INTERFACE
class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing inventory categories.

    list:
        Retrieve a list of categories.

    retrieve:
        Retrieve a single category.

    create/update/destroy:
        Inventory admin only.
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsInventoryAdminOrReadOnly]


# PUBLIC_INTERFACE
class InventoryItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing inventory items.

    list:
        Returns a paginated list of items suitable for tables and dashboards.
        Supports basic filtering via query parameters:
        - status
        - location
        - category
        - search (code or name)

    retrieve:
        Returns a detailed view of an item.

    create/update/destroy:
        Inventory admin only.
    """

    queryset = InventoryItem.objects.select_related("category", "location", "owner").all()
    permission_classes = [IsInventoryAdminOrReadOnly]

    def get_serializer_class(self):
        """
        Use a lightweight serializer for list actions, and a full serializer otherwise.
        """
        if self.action == "list":
            return InventoryItemListSerializer
        return InventoryItemDetailSerializer

    def get_queryset(self):
        """
        Apply filters based on query parameters to support dashboard use cases.
        """
        qs = super().get_queryset()
        params = self.request.query_params

        status_param = params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        location_param = params.get("location")
        if location_param:
            qs = qs.filter(location_id=location_param)

        category_param = params.get("category")
        if category_param:
            qs = qs.filter(category_id=category_param)

        active_param = params.get("is_active")
        if active_param is not None:
            if active_param.lower() in {"1", "true", "yes"}:
                qs = qs.filter(is_active=True)
            elif active_param.lower() in {"0", "false", "no"}:
                qs = qs.filter(is_active=False)

        search_param = params.get("search")
        if search_param:
            qs = qs.filter(
                models.Q(code__icontains=search_param)
                | models.Q(name__icontains=search_param),
            )

        return qs


# PUBLIC_INTERFACE
class MovementViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for tracking movements in the inventory.

    list:
        Retrieve movement history. Supports filters:
        - item
        - from_date, to_date (performed_at range)

    create:
        Register a new movement. The service layer will manage updates to
        stock quantities and automatic alerts.
    """

    queryset = Movement.objects.select_related(
        "item",
        "from_location",
        "to_location",
        "performed_by",
    ).all()
    serializer_class = MovementSerializer
    permission_classes = [IsInventoryAdminOrReadOnly]

    def get_queryset(self):
        """Filter movements based on query parameters."""
        qs = super().get_queryset()
        params = self.request.query_params

        item_param = params.get("item")
        if item_param:
            qs = qs.filter(item_id=item_param)

        from_date = params.get("from_date")
        to_date = params.get("to_date")
        if from_date:
            qs = qs.filter(performed_at__date__gte=from_date)
        if to_date:
            qs = qs.filter(performed_at__date__lte=to_date)

        return qs

    def perform_create(self, serializer):
        """
        Use the service layer to create the movement and apply business rules.

        The serializer is validated beforehand; we then delegate to
        register_movement and update the serializer instance.
        """
        validated = serializer.validated_data
        item = validated["item"]
        from_location = validated.get("from_location")
        to_location = validated.get("to_location")
        movement_type = validated["movement_type"]
        quantity = validated["quantity"]
        performed_by = validated.get("performed_by") or self.request.user
        performed_at = validated.get("performed_at") or timezone.now()
        notes = validated.get("notes", "")

        result = register_movement(
            item=item,
            from_location=from_location,
            to_location=to_location,
            movement_type=movement_type,
            quantity=quantity,
            performed_by=performed_by,
            performed_at=performed_at,
            notes=notes,
        )

        # Attach created instance so DRF can build a proper response
        serializer.instance = result.movement


# PUBLIC_INTERFACE
class ProcedureViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CRUD operations on procedures.

    list/retrieve:
        Visible to any authenticated user.

    create/update/destroy:
        Restricted to inventory admins.
    """

    queryset = Procedure.objects.all()
    serializer_class = ProcedureSerializer
    permission_classes = [IsInventoryAdminOrReadOnly]


# PUBLIC_INTERFACE
class AlertViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for listing and resolving alerts.

    list:
        Retrieve alerts, with filters by level, active state, and item.

    retrieve:
        Retrieve a single alert.

    partial_update:
        Used mainly to resolve alerts (set is_active=False, resolved_at).
        Restricted to inventory admins.
    """

    queryset = Alert.objects.select_related("item").all()
    serializer_class = AlertSerializer
    permission_classes = [IsInventoryAdminOrReadOnly]

    def get_queryset(self):
        """Allow filtering alerts via query parameters."""
        qs = super().get_queryset()
        params = self.request.query_params

        level = params.get("level")
        if level:
            qs = qs.filter(level=level)

        is_active = params.get("is_active")
        if is_active is not None:
            if is_active.lower() in {"1", "true", "yes"}:
                qs = qs.filter(is_active=True)
            elif is_active.lower() in {"0", "false", "no"}:
                qs = qs.filter(is_active=False)

        item_param = params.get("item")
        if item_param:
            qs = qs.filter(item_id=item_param)

        return qs

    def partial_update(self, request, *args, **kwargs):
        """
        Custom partial_update so that setting is_active=False will also
        populate resolved_at if missing.
        """
        instance = self.get_object()
        data = request.data.copy()

        # If client deactivates the alert and does not provide resolved_at,
        # set it automatically.
        is_active = data.get("is_active")
        if is_active is not None and str(is_active).lower() in {"0", "false", "no"}:
            if not data.get("resolved_at"):
                data["resolved_at"] = timezone.now().isoformat()

        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data, status=status.HTTP_200_OK)


# PUBLIC_INTERFACE
class AdminOnlyMetricsViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Simple placeholder ViewSet for future admin-only metrics endpoints.

    Currently this ViewSet is not wired into URLs, but it demonstrates the
    intended pattern for metrics-related APIs.
    """

    permission_classes = [IsInventoryAdmin]

    def list(self, request, *args, **kwargs):  # type: ignore[override]
        """
        Return a very simple static metrics payload.

        This can be replaced in later iterations with real aggregate queries.
        """
        data = {
            "status": "ok",
            "message": "Metrics endpoint not yet implemented.",
        }
        return Response(data)


# PUBLIC_INTERFACE
class RegisterUserView(generics.CreateAPIView):
    """
    Endpoint for registering new users with a specific inventory role.

    This endpoint is mounted at /api/auth/register and requires the caller
    to be authenticated with a role of admin or manager (or staff/superuser).

    Request body:
        - username (string, required)
        - password (string, required, write-only)
        - email (string, optional)
        - first_name (string, optional)
        - last_name (string, optional)
        - role (one of: admin, manager, viewer, technician)

    Response:
        201 Created with the created user data (without password),
        including the assigned profile role.
    """

    serializer_class = UserRegistrationSerializer
    permission_classes = [IsAdminOrManagerRole]


# PUBLIC_INTERFACE
class MeView(generics.RetrieveAPIView):
    """
    Endpoint returning the current authenticated user's data and profile role.

    This endpoint is mounted at /api/auth/me and requires a valid JWT or
    authenticated session.

    Response:
        200 OK with a JSON representation of the current user, including:
        - id, username, first_name, last_name, email
        - is_active, is_staff, is_superuser
        - profile: { role }
    """

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """
        Return the currently authenticated user instance.
        """
        return self.request.user
