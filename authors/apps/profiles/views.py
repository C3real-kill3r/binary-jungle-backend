from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from authors.apps.authentication.models import User
from .models import Profile
from .serializers import ProfileSerializer
from .renderers import ProfileJSONRenderer

from authors.apps.core.exceptions import ProfileDoesNotExist


class ProfileListView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ProfileSerializer
    renderer_classes = (ProfileJSONRenderer,)

    def get(self, request, *args, **kwargs):
        """
        Get a listing of user profiles. Excludes the requester.
        """
        try:
            queryset = Profile.objects.all().exclude(user=request.user)
        except Profile.DoesNotExist:
            raise ProfileDoesNotExist
        serializer = self.serializer_class(queryset, many=True)
        return Response({'profiles': serializer.data}, status=status.HTTP_200_OK)


class ProfileGetView(APIView):
    """Lists fetches a single profile and also updates a specific profile"""

    permission_classes = (IsAuthenticated,)
    serializer_class = ProfileSerializer
    renderer_classes = (ProfileJSONRenderer,)

    def get(self, request, username):
        """Fetches a specific profile filtered by the username"""

        try:
            profile = Profile.objects.get(user__username=username)
        except Profile.DoesNotExist:
            raise ProfileDoesNotExist

        serializer = self.serializer_class(profile)
        return Response({'profile': serializer.data}, status=status.HTTP_200_OK)

    def put(self, request, username):
        """Allows authenticated users to update only their profiles."""
        data = request.data

        serializer = self.serializer_class(instance=request.user.profile, data=data, partial=True)
        serializer.is_valid()
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class FollowMixin(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ProfileSerializer

    def get_user_profile(self, username):
        """
        Get profile by username.
        """
        user = get_object_or_404(User, username=username)
        return user.profile


class FollowUnFollowView(FollowMixin):
    renderer_classes = (ProfileJSONRenderer,)

    def get_auth_profile(self, request):
        """
        Get profile of the current authenticated user.
        """
        return request.user.profile

    def get_response(self, request, profile):
        """
        Generates an appropriate message for a follow or un -follow operation.
        """
        serializer = self.serializer_class(profile)

        if request.method == 'POST':
            message = 'You followed %s.'
        else:
            message = 'You un followed %s.'

        return {
            'profile': serializer.data,
            'message': message % profile.username
        }

    def check_self(self, request, prof_a, prof_b):
        """
        Checks that the user is not trying to follow or un follow self.
        """
        if prof_a == prof_b:
            if request.method == 'POST':
                message = 'You cannot follow yourself.'
            else:
                message = 'You cannot follow or un follow yourself.'
            raise ValidationError(message)

    def post(self, request, username):
        """
        Follow a user.
        """
        auth_profile = self.get_auth_profile(request)
        other_profile = self.get_user_profile(username)

        self.check_self(request, auth_profile, other_profile)

        # follow profile
        auth_profile.follow(other_profile)

        response = self.get_response(request, other_profile)

        return Response(response, status=status.HTTP_200_OK)

    def delete(self, request, username):
        """
        Un-follow a user.
        """
        auth_profile = self.get_auth_profile(request)
        other_profile = self.get_user_profile(username)

        self.check_self(request, auth_profile, other_profile)

        # un-follow profile
        auth_profile.un_follow(other_profile)

        response = self.get_response(request, other_profile)

        return Response(response, status=status.HTTP_200_OK)


class FollowersView(FollowMixin):
    def get(self, request, username):
        """
        Get followers list for user with specified username.
        """
        profile = self.get_user_profile(username=username)
        serializer = self.serializer_class(profile.followers(), many=True)
        data = {
            'username': username,
            'followers': serializer.data
        }
        return Response(data, status=status.HTTP_200_OK)


class FollowingView(FollowMixin):
    def get(self, request, username):
        """
        Get following list for user with specified username.
        """
        profile = self.get_user_profile(username=username)
        serializer = self.serializer_class(profile.following(), many=True)
        data = {
            'username': username,
            'following': serializer.data
        }
        return Response(data, status=status.HTTP_200_OK)

class FollowingUserView(FollowMixin):
    def get(self, request, username):
        """
        Determine whether auth user is following user with username.
        """
        auth_profile = request.user.profile
        other_profile = self.get_user_profile(username)
        is_following = other_profile.followed_by.filter(user=auth_profile.user).exists()
        data = {
            "following_status": is_following
        }
        return Response(data, status=status.HTTP_200_OK);
