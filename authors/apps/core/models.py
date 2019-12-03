from django.db import models
from django.utils import timezone


class TimestampsMixin(models.Model):
    """
    The TimestampsMixin has two fields, created_at and updated_at, used to determine
    when the model was created and when it was updated respectively.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Set the model as abstract to prevent migrations from being created
        abstract = True

        # Will be ordered in order of models created first by default
        ordering = ['-created_at', '-updated_at', '-id']


class SoftDeleteManager(models.Manager):
    """
    We are using this manager to remove results that are soft-deleted
    from the queryset.
    """
    def __init__(self, *args, **kwargs):
        self.with_deleted = kwargs.pop('deleted', False)
        super().__init__(*args, **kwargs)

    def __base_queryset(self):
        return super().get_queryset().filter(deleted_at=None)

    def get_queryset(self):
        query_set = self.__base_queryset()
        if self.with_deleted:
            return query_set
        return query_set.filter(deleted_at=None)


class SoftDeleteMixin(models.Model):
    """
    This mixin adds the ability to soft delete a model. This is achieved by using the
    deleted_at field. The field is always null. When the model is deleted the field
    is given the current timestamp.
    """
    class Meta:
        abstract = True

    objects = SoftDeleteManager()
    objects_with_deleted = SoftDeleteManager(deleted=True)

    deleted_at = models.DateTimeField(null=True)

    def delete(self, using=None, keep_parents=False, hard=False):
        """
        Hard delete model. To hard delete set hard to true.
        """
        if hard:
            super().delete(using=using, keep_parents=keep_parents)
        else:
            self.deleted_at = timezone.now()
            self.save()

    def restore(self):
        """
        Restore a soft deleted model.
        """
        self.deleted_at = None
        self.save()
