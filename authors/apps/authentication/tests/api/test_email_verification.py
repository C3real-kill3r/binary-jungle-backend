from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from django.core import mail
from rest_framework.reverse import reverse
from rest_framework.test import APIRequestFactory

from authors.apps.authentication.models import User
from authors.apps.authentication.tests.api.test_auth import AuthenticationTestCase
from authors.apps.authentication.views import RegistrationAPIView, AccountVerificationView


class TestEmailVerification(AuthenticationTestCase):

    def setUp(self):
        super().setUp()
        self.register()

    def verify_account(self, token, uid):
        request = APIRequestFactory().get(
            reverse("authentication:activate-account", kwargs={"token": token, "uid": uid}))

        account_verification = AccountVerificationView.as_view()
        response = account_verification(request, token=token, uid=uid)

        return response

    def test_sends_email(self):
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Activate your Author's Haven account.")

    def test_account_verified(self):
        """
        Tests whether the account verification was successful
        :return:
        """
        user = User.objects.get()
        token, uid = RegistrationAPIView.send_account_activation_email(user=user, send_email=False)
        response = self.verify_account(token, uid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user = User.objects.get()
        self.assertTrue(user.is_verified)

    def test_invalid_verification_link(self):
        """
        Ensure an invalid verification link does not verify a user
        :return:
        """
        user = User.objects.get()
        token, uid = RegistrationAPIView.send_account_activation_email(user=user, send_email=False)

        # create the uid from a different username
        uid = urlsafe_base64_encode(force_bytes("invalid_username")).decode("utf-8")

        response = self.verify_account(token, uid)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        user = User.objects.get()
        # Ensure the user is not verified
        self.assertFalse(user.is_verified)
