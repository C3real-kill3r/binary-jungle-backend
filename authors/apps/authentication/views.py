import os

from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.db import IntegrityError
from django.utils.encoding import force_bytes, force_text
from rest_framework import status
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.generics import RetrieveUpdateAPIView, CreateAPIView, ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from requests.exceptions import HTTPError

from authors.apps.articles.pagination import StandardResultsSetPagination
from authors.apps.core import client
from authors.apps.core.renderers import BaseJSONRenderer
from .renderers import UserJSONRenderer

from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

from social_django.utils import load_backend, load_strategy

from social_core.backends.oauth import BaseOAuth1, BaseOAuth2
from social_core.exceptions import MissingBackend, AuthAlreadyAssociated
from .serializers import (
    LoginSerializer, RegistrationSerializer, UserSerializer, ForgotPasswordSerializer, ResetPasswordSerializers,
    SocialSignUpSerializer, LogoutSerializer
)
from authors.apps.profiles.serializers import ProfileSerializer
from .models import User, BlacklistedToken
from authors.apps.profiles.models import Profile
from rest_framework import authentication


class RegistrationAPIView(CreateAPIView):
    # Allow any user (authenticated or not) to hit this endpoint.
    permission_classes = (AllowAny,)
    renderer_classes = (UserJSONRenderer,)
    serializer_class = RegistrationSerializer

    def post(self, request, *args, **kwargs):
        user = request.data.get('user', {})

        # The create serializer, validate serializer, save serializer pattern
        # below is common and you will see it a lot throughout this course and
        # your own work later on. Get familiar with it.
        serializer = self.serializer_class(data=user)
        serializer.validate_username(user["username"])
        serializer.validate_email(user["email"])
        serializer.validate_password(user["password"])

        serializer.is_valid(raise_exception=True)
        serializer.save()

        user = User.objects.filter(email=user['email']).first()

        RegistrationAPIView.send_account_activation_email(user, request)

        data = serializer.data
        data['message'] = 'We have sent you an activation link'
        return Response(data, status=status.HTTP_201_CREATED)

    @staticmethod
    def send_account_activation_email(user, request=None, send_email=True):
        """

        :param user:
        :param request:
        :param send_email: Testing will pass this as false in order to prevent actually sending an email to mock users
        :return:
        """
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.username)).decode("utf-8")

        if send_email:
            email = user.email
            username = user.username
            from_email = os.getenv("EMAIL_HOST_SENDER")

            email_subject = 'Activate your Author\'s Haven account.'
            email_message = render_to_string('email_verification.html', {
                'activation_link': client.get_activate_account_link(token, uid),
                'title': email_subject,
                'username': username
            })
            text_content = strip_tags(email_message)
            msg = EmailMultiAlternatives(
                email_subject, text_content, from_email, to=[email])
            msg.attach_alternative(email_message, "text/html")
            msg.send()

        return token, uid


class LoginAPIView(CreateAPIView):
    permission_classes = (AllowAny,)
    renderer_classes = (UserJSONRenderer,)
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        user = request.data.get('user', {})

        # Notice here that we do not call `serializer.save()` like we did for
        # the registration endpoint. This is because we don't actually have
        # anything to save. Instead, the `validate` method on our serializer
        # handles everything we need.
        serializer = self.serializer_class(data=user)
        serializer.is_valid(raise_exception=True)

        user = User.objects.get(email=user['email'])
        # return jwt as the response
        resp = ProfileSerializer(user.profile).data
        resp['token'] = serializer.data['token']

        return Response(resp, status=status.HTTP_200_OK)


class UserRetrieveUpdateAPIView(RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    renderer_classes = (UserJSONRenderer,)
    serializer_class = UserSerializer

    def retrieve(self, request, *args, **kwargs):
        # There is nothing to validate or save here. Instead, we just want the
        # serializer to handle turning our `User` object into something that
        # can be JSONified and sent to the client.
        serializer = self.serializer_class(request.user)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        serializer_data = request.data.get('user', {})
        # Here is that serialize, validate, save pattern we talked about
        # before.
        serializer = self.serializer_class(
            request.user, data=serializer_data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)


class AccountVerificationView(APIView):

    def get(self, request, token, uid):
        username = force_text(urlsafe_base64_decode(uid))

        user = User.objects.filter(username=username).first()
        validate_token = default_token_generator.check_token(user, token)

        data = {"message": "Congratulations! Your account has been activated. Please log in."}
        st = status.HTTP_200_OK

        if not validate_token:
            data['message'] = "Your activation link is Invalid or has expired. Kindly register."
            st = status.HTTP_400_BAD_REQUEST
        else:
            # Mark the user as verified
            user.is_verified = True
            user.save()

        return Response(data, status=st)


class ForgotPasswordView(CreateAPIView):
    """
    This view capture the email and generates a reset password token
    if the email has already been registered.
    """
    permission_classes = (AllowAny,)
    serializer_class = ForgotPasswordSerializer

    def post(self, request):
        email = request.data.get('email', "")
        user = User.objects.filter(email=email).first()

        if user is None:
            response = {"message": "An account with this email does not exist."}
            return Response(response, status.HTTP_400_BAD_REQUEST)

        # Generate token and get  site domain
        token = default_token_generator.make_token(user)
        # Required parameters for sending email
        subject, from_email, to_email = 'Password Reset Link', os.getenv("EMAIL_HOST_SENDER"), email

        reset_link = client.get_password_reset_link(token)

        # render with dynamic value
        html_content = render_to_string('email_reset_password.html', {'reset_password_link': reset_link})

        # Strip the html tag. So people can see the pure text at least.
        text_content = strip_tags(html_content)

        # create the email, and attach the HTML version as well.
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        response = {"message": "Please follow the link sent to your email to reset your password."}

        return Response(response, status.HTTP_200_OK)


class ResetPasswordView(APIView):
    """
    This view allows any user to update password
    """
    permission_classes = (AllowAny,)
    serializer_class = ResetPasswordSerializers

    def put(self, request, token):
        """
        Resets a users password and sends an email on successful reset
        """
        data = request.data
        email = data['email']
        # Adds token to data
        data['token'] = token
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        subject, from_email, to_email = 'Password reset notification', os.getenv("EMAIL_HOST_SENDER"), email

        html_content = render_to_string('email_reset_password_done.html')

        text_content = strip_tags(html_content)
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        response = {"message": "Your password has been successfully reset. You can now log in."}
        return Response(response, status.HTTP_200_OK)


class SocialSignUp(CreateAPIView):
    # Allow any user to hit this point
    permission_classes = (AllowAny,)
    renderer_classes = (UserJSONRenderer,)
    serializer_class = SocialSignUpSerializer

    def create(self, request, *args, **kwargs):
        """
        Override `create` instead of `perform_create` to access request
        request is necessary for `load_strategy`
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider = serializer.data.get('provider', None)

       # associates the social account if the request comes
         # from an authenticated user
        authed_user = request.user if not request.user.is_anonymous else None


       # By loading `request` to `load_strategy` `social-app-auth-django`
        # will know to use Django
        strategy = load_strategy(request)

        # Getting the backend that associates the user's social auth provider
        # eg Facebook, Twitter and Google

        try:
            backend = load_backend(strategy=strategy, name=provider, redirect_uri=None)
        except MissingBackend as e:
            return Response({
                "errors": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            if isinstance(backend, BaseOAuth1):
                # Twitter uses OAuth1 and requires an access_token_secret
                # to be passed in the authentication

                token = {
                    "access_token": serializer.data['access_token'],
                    "access_token_secret": request.data['access_token_secret']
                }
            elif isinstance(backend, BaseOAuth2):
                # oauths implicit grant type which is used for web
                # and mobile application, all we have to pass here is
                # an access_token

                token = serializer.data['access_token']
        except HTTPError as e:
            return Response({
                "error": {
                    "token": "invalid token",
                    "details": str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            # if `authed_user` is None `social-auth-app` will make a new user
            # else the social account will be associated with the user that is
            # passed in
            user = backend.do_auth(token, user=authed_user)

        except (AuthAlreadyAssociated, IntegrityError):
            # you can't associate a social account with more than one user
            return Response({
                "errors": "That social account is already in use"
            }, status=status.HTTP_400_BAD_REQUEST)
        if user and user.is_active:
            user.is_verified = True

        def get_image_url(self):
            """
            Get the user's current image url from the provider.
            save/update the image field of the particular user
            and returns the image_url.
            """
            try:
                if provider == "google-oauth2":
                    url = "http://picasaweb.google.com/data/entry/api/user/" \
                          "{}?alt=json".format(user.email)
                    data = requests.get(url).json()
                    image_url = data["entry"]["gphoto$thumbnail"]["$t"]

                elif provider == "facebook":
                    id_url = "https://graph.facebook.com/me?access_token={}" \
                        .format(access_token)
                    id_data = requests.get(id_url).json()
                    user_id = id_data["id"]
                    url = "http://graph.facebook.com/{}/picture?type=small" \
                        .format(user_id)
                    image_url = requests.get(url, allow_redirects=True).url

            except BaseException:
                image_url = ""

            user.image = image_url
            user.save()
            return image_url

        Profile.objects.get_or_create(user=user)
        serializer = UserSerializer(user)
        output = serializer.data
        user_in_db = User.objects.get(username=output['username'])
        output['image'] = get_image_url(self)
        output["token"] = user_in_db.token

        return Response(output, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """this class logs out a user"""

    permission_classes = (IsAuthenticated,)
    serializer_class = LogoutSerializer

    def delete(self, request):
        token = authentication.get_authorization_header(request).split()[1].decode()
        data = request.data
        data['token'] = token
        if BlacklistedToken.objects.filter(token=token).first():
            return Response({"success": "You have already logged out"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": "Succesfully logged out"}, status=status.HTTP_200_OK)


class UsersAPIView(ListAPIView):
    serializer_class = ProfileSerializer
    permission_classes = (AllowAny,)
    renderer_classes = (BaseJSONRenderer,)
    queryset = Profile.objects.all()
