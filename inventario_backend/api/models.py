"""
Database models for the api app.
"""

from django.db import models


class TimestampedModel(models.Model):
    """
    Abstract base model that adds created/updated timestamps.

    Can be extended by concrete inventory-related models in this app.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
