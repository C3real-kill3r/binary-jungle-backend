import json

from notifications.signals import notify
from rest_framework import status
from rest_framework.reverse import reverse

from authors.apps.articles.tests.api.test_articles import BaseArticlesTestCase
from authors.apps.authentication.tests.api.test_auth import AuthenticatedTestCase


class BaseNotificationsTestCase(AuthenticatedTestCase):
    DEFAULT_NOTIFICATION_COUNT = 10
    URLS = {
        'all': reverse("notifications:notifications"),
        'sent': reverse("notifications:sent-notifications"),
        'unsent': reverse("notifications:unsent-notifications"),
        'read': reverse("notifications:read-notifications"),
        'unread': reverse("notifications:unread-notifications")
    }

    def setUp(self):
        super().setUp()
        self.notification_type = "all"

    def get(self, notification_type=None):
        """
        Return a list of notifications and response_code
        :return:
        """
        response = self.client.get(self.URLS[notification_type or self.notification_type])
        return response.status_code, json.loads(response.content)

    def delete(self, notification_type=None):
        """
        Delete a list of notifications and return the response
        :return:
        """
        response = self.client.delete(self.URLS[notification_type or self.notification_type])
        return response.status_code, json.loads(response.content)

    def sendNotification(self, user=None, verb="sample", description="You have a notification"):
        """
        Helper method to send notification to a particular user
        :param user:
        :param verb:
        :param description:
        :return:
        """
        user = user or self.get_authenticated_user()
        notify.send(user, recipient=user, verb=verb, description=description)

    def sendManyNotifications(self, user=None, count=DEFAULT_NOTIFICATION_COUNT):
        """
        Helper method to send many notifications
        :param user:
        :param count:
        :return:
        """
        for i in range(0, count):
            self.sendNotification(user)


class AllNotificationsTestCase(BaseNotificationsTestCase):

    def setUp(self):
        super().setUp()
        self.sendManyNotifications()

    def test_get_all_notifications(self):
        """
        Test can list all the notifications in the system
        :return:
        """
        response_code, data = self.get()
        self.assertEqual(response_code, status.HTTP_200_OK)
        self.assertEqual(data['data']['count'], self.DEFAULT_NOTIFICATION_COUNT)

    def test_delete_all_notifications(self):
        """
        Test that can delete all the notifications
        :return:
        """
        status_code, data = self.delete()
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(data['status'], "success")

        status_code, data = self.get()
        self.assertEqual(data['data']['count'], 0)

    def test_unauthenticated_user_cannot_get_notifications(self):
        """
        Ensure an unauthenticated user cannot get notifications
        :return:
        """
        self.logout()
        status_code, data = self.get()
        self.assertEqual(status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_cannot_delete_notifications(self):
        """
        Ensure a user that is not authenticated cannot delete notifications
        :return:
        """
        self.logout()
        status_code, data = self.delete()
        self.assertEqual(status_code, status.HTTP_403_FORBIDDEN)

    def test_another_user_cannot_get_my_notifications(self):
        """
        Ensure a user only gets notifications that belong to them
        :return:
        """
        # login another user
        self.authenticate_another_user()
        status_code, data = self.get()
        self.assertEqual(data['data']['count'], 0)


class UnsentNotificationsTestCase(BaseNotificationsTestCase):

    def setUp(self):
        super().setUp()
        self.notification_type = "unsent"

    def test_notifications_first_unsent(self):
        """
        Ensure the notification status begins as unsent
        :return:
        """
        self.sendManyNotifications()
        status_code, data = self.get()
        self.assertEqual(data['data']['count'], self.DEFAULT_NOTIFICATION_COUNT)


class SentNotificationTestCase(BaseNotificationsTestCase):

    def setUp(self):
        super().setUp()
        self.notification_type = "sent"

    def test_notifications_sent_once_queried(self):
        """
        Notifications should be marked as sent once they are retrieved
        :return:
        """
        self.sendManyNotifications()
        status_code, data = self.get()
        self.assertEqual(data['data']['count'], 0)

        # get all notifications
        self.get(notification_type="all")

        # now check whether they exist in the sentbox
        status_code, data = self.get()
        self.assertEqual(data['data']['count'], self.DEFAULT_NOTIFICATION_COUNT)


class UnReadNotificationTestCase(BaseNotificationsTestCase):
    def setUp(self):
        super().setUp()
        self.notification_type = "unread"

    def notifications_unread_once_created(self):
        """
        Notifications should be unread by default
        :return:
        """
        self.sendManyNotifications()
        status_code, data = self.get()
        self.assertEqual(data['data']['count'], self.DEFAULT_NOTIFICATION_COUNT)


class ReadNotificationsTestCase(BaseNotificationsTestCase):
    def setUp(self):
        super().setUp()
        self.notification_type = "read"

    def read_notifications(self, data):
        notifications = data['data']['notifications']
        if len(notifications) != 1:
            for notification in data['data']['notifications']:
                self.client.put(
                    reverse("notifications:read-notification", kwargs={'pk': notification['id']})
                )
        else:
            return self.client.put(
                reverse("notifications:read-notification", kwargs={'pk': notifications[0]['id']})
            )

    def test_can_read_notification(self):
        """
        Ensure a notification can be marked as read
        :return:
        """
        self.sendNotification()
        status_code, data = self.get(notification_type='unread')
        # mark the notification as read
        response = self.read_notifications(data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        status_code, data = self.get()
        self.assertEqual(data['data']['count'], 1)

    def test_can_get_read_notifications(self):
        """
        Ensure notifications after read can be queried
        :return:
        """
        self.sendManyNotifications()

        status_code, data = self.get(notification_type='unread')
        self.read_notifications(data=data)

        status_code, data = self.get()
        self.assertEqual(data['data']['count'], self.DEFAULT_NOTIFICATION_COUNT)


class NotificationSubscriptionTestCase(AuthenticatedTestCase):

    def subscribe(self):
        """
        Helper method to subscribe to emails
        :return:
        """
        return self.client.post(reverse("notifications:subscribe"))

    def unsubscribe(self):
        """
        Helper method to unsubscribe from emails
        :return:
        """
        return self.client.delete(reverse("notifications:subscribe"))

    def subscription_status(self):
        """
        Helper method to fetch subscription status.
        :return:
        """
        return self.client.get(reverse("notifications:subscription-status"))

    def test_user_can_subscribe_to_the_notifications(self):
        """
        Ensure after subscription, a user can get back to subscription
        :return:
        """
        response = self.subscribe()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b'You have successfully subscribed to our notifications.', response.content)
        self.assertTrue(response.data['message']['subscription_status'])

    def test_user_can_unsubscribe_from_notifications(self):
        """
        Ensure a user can opt to unsubscribe from notifications
        :return:
        """
        response = self.unsubscribe()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b'You have successfully unsubscribed from our notifications.', response.content)
        self.assertFalse(response.data['message']['subscription_status'])

    def test_user_can_get_their_subscription_status(self):
        self.subscribe()
        response = self.subscription_status()
        self.assertTrue(response.data['subscription_status'])
        self.unsubscribe()
        response = self.subscription_status()
        self.assertFalse(response.data['subscription_status'])


class ArticleNotificationTestCase(BaseArticlesTestCase, BaseNotificationsTestCase):

    def test_user_gets_notification_upon_article_creation(self):
        """
        Ensure a user gets an email when they are subscribed
        :return:
        """
        # login another user to follow
        self.register_and_login(self.user2)

        # follow the first user
        self.client.post(reverse("profiles:follow", kwargs={'username': self.user['user']['username']}))

        # login as first user and create an article
        self.login(self.user)
        self.create_article(published=True)

        # login as second user and check notifications
        self.login(self.user2)
        status_code, data = self.get(notification_type='unsent')
        self.assertEqual(data['data']['count'], 1)

    def test_author_gets_notification_upon_article_favoriting(self):
        """
        Ensure a author gets a notification in their unread box after his article has been rated
        :return:
        """
        # login another user to favorite
        self.register_and_login(self.user2)

        # login as first user and create an article
        self.login(self.user)
        self.create_article(published=True)
        slug = self.create_article()['slug']

        # login as second user, favorite
        self.login(self.user2)
        self.client.post(reverse(
            'articles:favourite_article', kwargs={'slug': slug}), format='json')
        # login as first user and check notification
        self.login(self.user)
        status_code, data = self.get(notification_type='unsent')
        self.assertEqual(data['data']['count'], 1)

    def test_author_gets_notification_upon_article_commenting(self):
        """
        Ensure author gets a notification in their unread box after article has been commented on
        :return:
        """
        # login another user to comment
        self.register_and_login(self.user2)

        # login as first user and create an article
        self.login(self.user)
        self.create_article(published=True)
        slug = self.create_article()['slug']

        # login as second user, comment on article
        self.login(self.user2)
        comment = {"comment": {"body": "comment on this "}}
        response = self.client.post(reverse(
            "articles:comments", kwargs={'slug': slug}), data=comment, format="json")
        # login as first user and check notification
        self.login(self.user)
        status_code, data = self.get(notification_type='unsent')
        self.assertEqual(data['data']['count'], 1)

    def test_author_gets_notification_upon_article_rating(self):
        """
        Ensure author gets a notification in their unread box after artile has been rated
        :return:
        """
        # login another user to rating
        self.register_and_login(self.user2)

        # login as first user and rating an article
        self.login(self.user)
        self.create_article(published=True)
        slug = self.create_article()['slug']

        # login as second user, rating on article
        self.login(self.user2)
        rating = {"rating": {"rating": 4}}
        response = self.client.post(reverse(
            "articles:rate-article", kwargs={'slug': slug}), data=rating, format="json")
        # login as first user and check notification
        self.login(self.user)
        status_code, data = self.get(notification_type='unsent')
        self.assertEqual(data['data']['count'], 0)
