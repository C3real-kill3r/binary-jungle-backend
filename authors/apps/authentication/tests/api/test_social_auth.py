"""
Test for the social authentication with Google
"""
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch
from authors.apps.authentication.models import User

access_token = '''
EAAJrz4Wyof4BALP69kKhbavn0orNiZACWttkmT
xdYeapBJR487dpLnIWaBmKaGnYJxyRI09OdRF8krBOL6isVZBZC1rZCo6
acc9sZBymZBX0ZB83WmWOPj6vzRrPtTdqZBxceZCnFjPtaoJjJCbHeuXsH
4LzeKHfe5MMR2dpz0qe2M3maZBznrxsNRQWl37qxCvlCelZCiVEDoZCTtn
wDdV0zZC84tsqQIDPQN9CiitF2K6jvRgZDZD
'''


class SocialAuthTest(APITestCase):
    """
    Base Test Class for the Social Authentication
    """
    def setUp(self):
        """
        Setup for tests
        """
        # Set up the social_auth url.
        self.auth_url = reverse("authentication:social")

        self.client = APIClient()

        self.user = User(
            username='Foo',
            email='bar@example.com',
            password='123qwerty',
            is_active=True)
        self.user.save()


    def test_provider_in_payload(self):
        """
        Test that the OAuth provider is included in request
        """
        payload = {
            "provider": "",
            "access_token": access_token
        }
        res = self.client.post(
            reverse("authentication:social"),
            payload,
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_access_token_in_payload(self):
        """
        Test that the OAuth access_token is provided
        """
        payload = {
            "provider": "facebook",
            "access_token": ""
        }
        res = self.client.post(
            reverse("authentication:social"),
            payload,
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_access_token_is_valid(self):
        """
        When access_token is included in payload, check for validity
        """
        payload = {
            "provider": "facebook",
            "access_token": access_token + "FAKETOKEN"
        }
        res = self.client.post(
            reverse("authentication:social"),
            payload,
            format='json'
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_provider(self):
        """
        Test request without passing the provider
        """
        access_token = "EAAexjwrTz4IBAC2T3cPCtLdLS3fUGVEz9Ma37"
        data = {"access_token": access_token}
        response = self.client.post(self.auth_url, data=data)
        self.assertEqual(response.status_code, 400)

    def test_invalid_provider(self):
        """
        Test giving a non-existent provider
        """
        access_token = "EAAexjwrTz4IBAC2T3cPCtLdLS3fUGVEz9Ma37"
        data = {"access_token": access_token, "provider": "facebook-oauth23"}
        response = self.client.post(self.auth_url, data=data)
        self.assertEqual(response.status_code, 400)

    def test_invalid_token(self):
        """
        Test an invalid access token
        """
        access_token = "Invalid token"
        data = {"access_token": access_token, "provider": "goolgle"}
        response = self.client.post(self.auth_url, data=data)
        self.assertEqual(response.status_code, 400)
