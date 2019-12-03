import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from authors.apps.core.test_helpers import set_test_client, create_user, login


class FollowBaseTestCase(APITestCase):
    def setUp(self):
        set_test_client(self.client)
        self.mr_foo = create_user(overrides={'username': 'mr_foo'})
        self.mr_bar = create_user(overrides={'username': 'mr_bar'})
        self.mr_baz = create_user(overrides={'username': 'mr_baz'})
        self.mr_joe = create_user(overrides={'username': 'mr_joe'})

    def follow(self, username):
        return self.client.post(reverse('profiles:follow', kwargs={'username': username}))

    def un_follow(self, username):
        return self.client.delete(reverse('profiles:follow', kwargs={'username': username}))

    def followers(self, username):
        return self.client.get(reverse('profiles:followers', kwargs={'username': username}))

    def following(self, username):
        return self.client.get(reverse('profiles:following', kwargs={'username': username}))


class FollowTestCase(FollowBaseTestCase):
    """
    Tests the ability of a user to follow other users.
    """

    def test_user_can_follow_users(self):
        """
        Authenticated users should be able to follow other users.
        """
        login(self.mr_foo)
        response = self.follow('mr_baz')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_cannot_follow_themselves(self):
        """
        Users cannot follow themselves. It makes no logical sense. :)
        """
        login(self.mr_foo)
        response = self.follow('mr_foo')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('You cannot follow yourself.', response.data['errors'])

    def test_unauthenticated_user_cannot_follow_users(self):
        """
        Unauthenticated users cannot follow other users.
        """
        response = self.follow('mr_foo')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UnFollowTestCase(FollowBaseTestCase):
    """
    Tests the ability of a user to un follow those they are currently following.
    """

    def test_user_can_un_follow_users(self):
        """
        Authenticated users should be able to un-follow users they are currently following.
        """
        # let 'mr_foo' follow then un-follow 'mr_baz'
        login(self.mr_foo)
        # follow
        self.follow('mr_baz')
        # un-follow
        response = self.un_follow('mr_baz')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_cannot_un_follow_themselves(self):
        """
        Users should be able to un-follow themselves. It does not make any logical sense.
        """
        # let 'mr_foo' attempt to follow self
        login(self.mr_foo)
        response = self.un_follow('mr_foo')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('You cannot follow or un follow yourself.', json.dumps(response.data))

    def test_unauthenticated_user_cannot_un_follow_users(self):
        """
        Unauthenticated users cannot un-follow users.
        """
        response = self.un_follow('mr_foo')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class FollowingTestCase(FollowBaseTestCase):
    """
    Tests the ability of a user to retrieve following list.
    """

    def test_user_can_see_following_list(self):
        """
        Authenticated users can retrieve their following list.
        """
        login(self.mr_foo)
        # let 'mr_foo' follow both 'mr_bar' and 'mr_baz'
        self.follow('mr_bar')
        self.follow('mr_baz')
        # retrieve mr_foo's following
        response = self.following('mr_foo')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # assert that 'mr_bar' and 'mr_baz' are on the following list
        data = json.dumps(response.data)
        self.assertIn('mr_bar', data)
        self.assertIn('mr_baz', data)

    def test_user_can_see_other_users_following_list(self):
        """
        Authenticated users can retrieve others following list.
        """
        login(self.mr_foo)
        # let 'mr_foo' follow both 'mr_bar' and 'mr_baz'
        self.follow('mr_bar')
        self.follow('mr_baz')
        login(self.mr_joe)
        # let mr_joe retrieve mr_foo's following
        response = self.following('mr_foo')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # assert that 'mr_bar' and 'mr_baz' are on the following list
        data = json.dumps(response.data)
        self.assertIn('mr_bar', data)
        self.assertIn('mr_baz', data)

    def test_unauthenticated_user_cannot_see_following_list(self):
        """
        Unauthenticated users cannot retrieve following list.
        """
        response = self.following('mr_foo')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class FollowersTestCase(FollowBaseTestCase):
    """
    Tests the ability of a user to retrieve followers list.
    """

    def test_user_can_see_followers_list(self):
        """
        Authenticated users can retrieve followers list.
        """
        # let 'mr_bar' and 'mr_baz' follow 'mr_foo'
        login(self.mr_bar)
        self.follow('mr_foo')
        login(self.mr_baz)
        self.follow('mr_foo')
        # retrieve mr_foo's followers
        response = self.followers('mr_foo')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # assert that 'mr_bar' and 'mr_baz' are on the followers list
        data = json.dumps(response.data)
        self.assertIn('mr_bar', data)
        self.assertIn('mr_baz', data)

    def test_user_can_see_other_users_followers_list(self):
        """
        Authenticated users can retrieve others followers list.
        """
        # let 'mr_bar' and 'mr_baz' follow 'mr_foo'
        login(self.mr_bar)
        self.follow('mr_foo')
        login(self.mr_baz)
        self.follow('mr_foo')
        login(self.mr_joe)
        # let mr_joe retrieve mr_foo's followers
        response = self.followers('mr_foo')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # assert that 'mr_bar' and 'mr_baz' are on the followers list
        data = json.dumps(response.data)
        self.assertIn('mr_bar', data)
        self.assertIn('mr_baz', data)

    def test_unauthenticated_user_cannot_see_followers_list(self):
        """
        Unauthenticated users cannot retrieve followers list.
        """
        response = self.followers('mr_foo')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

class FollowingUserTestCase(FollowBaseTestCase):
    def is_following_me(self, username):
        return self.client.get(reverse("profiles:is-following", kwargs={"username": username}))

    def test_user_can_check_if_they_re_followed_by_others(self):
        """
        Authenticated users can check whether they're being followed.
        """
        # let 'mr_foo' check whether 'mr_bar' is following them
        login(self.mr_foo)
        response = self.is_following_me('mr_bar')
        self.assertEqual(response.data, {"following_status": False})

        # let 'mr_bar' follow 'mr_foo'
        login(self.mr_bar)
        self.follow('mr_foo')
        # let 'mr_foo' check whether 'mr_bar' is following them
        login(self.mr_foo)
        response = self.is_following_me('mr_bar')
        login(self.mr_bar)
        response2 = self.is_following_me('mr_foo')
        self.assertEqual(response.data, {"following_status": False})
        self.assertEqual(response2.data, {"following_status": True})

    def test_unauthenticated_users_cannot_check_if_they_re_followed_by_others(self):
        """
        Unauthenticated users cannot check whether they're being followed.
        """
        response = self.is_following_me('mr_bar')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
