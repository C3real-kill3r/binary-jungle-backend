import json

from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.reverse import reverse
from django.contrib.auth.tokens import default_token_generator
from authors.apps.authentication.models import User


class TestSendEmail(APITestCase):
    """
    Tests that an email is sent to a user(a registered user)
    """

    def setUp(self):
        """
        Create a user to test the email functionality
        """
        self.forgot_password_url = reverse('authentication:forgot-password')
        self.register_url = reverse('authentication:user-register')
        self.user = {
            'user': {
                'username': 'kiki',
                'email': 'kiki@gmail.com',
                'password': 'Pass3#$%/:='
            }
        }
        self.client.post(self.register_url, self.user, format="json")

    def test_invalid_email(self):
        """
        Tests whether an email can be sent to unregistered user
        """
        response = self.client.post(
            self.forgot_password_url,
            data={"email": "kikidoylm@gmail.com"},
            format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.content,
            b'{"message":"An account with this email does not exist."}')

    def test_valid_email(self):
        """
        Tests if email will be sent to a registered user
        """
        response = self.client.post(
            self.forgot_password_url,
            data={'email': self.user['user']['email']}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_empty_email(self):
        """
        Test if a user can get an email without providing an email
        """
        response = self.client.post(
            self.forgot_password_url, data={"email": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.content,
            b'{"message":"An account with this email does not exist."}')


class TestResetPassword(APITestCase):
    """
    Tests if a registered user can edit their email
    """

    def setUp(self):
        """
        Creates a test user
        """
        self.user = {
            'user': {
                'username': 'kiki',
                'email': 'kiki@gmail.com',
                'password': 'Kiki1234@?/5'
            }
        }
        self.register_url = reverse('authentication:user-register')
        self.client.post(self.register_url, self.user, format="json")
        email = self.user['user']['email']
        user = User.objects.filter(email=email).first()
        token = default_token_generator.make_token(user)
        self.reset_url = reverse(
            "authentication:reset-password", kwargs={"token": token})

    def test_valid_password(self):
        """
        Tests if a user can reset a password
        """
        data = {
            "email": "kiki@gmail.com",
            "password": "Kiki123455",
            "confirm_password": "Kiki123455"
        }
        response = self.client.put(self.reset_url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.content,
            b'{"message":"Your password has been successfully reset. You can now log in."}')

    def test_empty_password(self):
        """
        Tests if a user can reset a password with an empty field
        """
        data = {
            "email": "kiki@gmail.com",
            "password": "",
            "confirm_password": ""
        }
        response = self.client.put(self.reset_url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "This field may not be blank.",
            json.loads(response.content)['errors']['password'],
        )

    def test_unmatching_password(self):
        """
        test if a user can reset password with a unmatching passwords
        """
        data = {
            "email": "kiki@gmail.com",
            "password": "Kikidylm12",
            "confirm_password": "Kikidylm1"
        }
        response = self.client.put(self.reset_url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.content, b'{"errors":{"error":["The passwords do not match."]}}')

    def test_invalid_password(self):
        """
        test whether the user can reset password using an invalid password
        """
        data = {
            "email": "kiki@gmail.com",
            "password": "Kiki",
            "confirm_password": "Kiki"
        }
        response = self.client.put(self.reset_url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Ensure this field has at least 8 characters.",
            json.loads(response.content)['errors']['password']
        )

    def test_used_token(self):
        """
        tests if a user can reuse a token
        """
        data = {
            "email": "kiki@gmail.com",
            "password": "Kiki123455",
            "confirm_password": "Kiki123455"
        }
        data2 = {
            "email": "kiki@gmail.com",
            "password": "Kiki1234",
            "confirm_password": "Kiki1234"
        }
        response = self.client.put(self.reset_url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.content,
            b'{"message":"Your password has been successfully reset. You can now log in."}')
        response2 = self.client.put(self.reset_url, data=data2, format="json")
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response2.content,
            b'{"errors":{"error":["Something went wrong. Try again."]}}'
        )
