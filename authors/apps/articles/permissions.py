from rest_framework import permissions


class IsArticleOwnerOrReadOnly(permissions.BasePermission):
    """
    Use this class to restrict users from manipulating articles that do not belong to them

    It is an object-level permission that only allows owners of an object to edit it.

    """
    message = "You are not allowed to modify this article."

    def has_object_permission(self, request, view, obj):
        # the safe methods are implemented independently in the articles mixins, no need for the implementation here.
        return obj.author == request.user


class IsNotArticleOwner(permissions.BasePermission):
    message = "You cannot perform this action on your own article"

    def has_object_permission(self, request, view, obj):
        return obj.author != request.user
