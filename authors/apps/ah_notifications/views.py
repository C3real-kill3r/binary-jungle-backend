from notifications.models import Notification
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from authors.apps.ah_notifications.serializers import NotificationSerializer
from authors.apps.core.renderers import BaseJSONRenderer
from rest_framework.views import APIView
from authors.apps.authentication.models import User
from authors.apps.core.mail_sender import send_email


class NotificationAPIView(generics.ListAPIView, generics.DestroyAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = NotificationSerializer
    renderer_classes = (BaseJSONRenderer,)

    def get(self, request, *args, **kwargs):
        notifications = self.notifications(request)
        serializer = self.serializer_class(notifications, many=True, context={'request': request})

        return Response({"count": notifications.count(), "notifications": serializer.data})

    def destroy(self, request, *args, **kwargs):
        notifications = self.notifications(request)
        count = notifications.count()
        notifications.mark_all_as_deleted()

        return Response({"message": "{} notifications deleted".format(count)})

    def notifications(self, request):
        pass


class AllNotificationsAPIView(NotificationAPIView):
    """
    List all the notifications for this user
    """

    def notifications(self, request):
        request.user.notifications.mark_as_sent()
        return request.user.notifications.active()


class UnreadNotificationsAPIView(NotificationAPIView):
    """
    List all unread notifications for this user
    """

    def notifications(self, request):
        request.user.notifications.mark_as_sent()
        return request.user.notifications.unread()


class ReadNotificationsAPIView(NotificationAPIView, generics.UpdateAPIView):
    """
    List all the Read  notifications for this user
    """

    def update(self, request, *args, **kwargs):
        pk = kwargs['pk']
        try:
            notification = Notification.objects.get(pk=pk)
        except Notification.DoesNotExist:
            return Response({"error": "Notification not found"}, status.HTTP_404_NOT_FOUND)

        notification.mark_as_read()
        return Response({"message": "Notification has been read"})

    def notifications(self, request):
        return request.user.notifications.read()


class UnsentNotificationsAPIView(NotificationAPIView):
    """
    List all the unsent notifications
    """

    def notifications(self, request):
        return request.user.notifications.unsent()


class SentNotificationsAPIView(NotificationAPIView):
    """
    List all the sent notifications for this user
    """

    def notifications(self, request):
        return request.user.notifications.active().sent()


class SubscribeAPIView(APIView):
    """
    Allow users to subscribe to notifications
    """
    permission_classes = (IsAuthenticated,)
    renderer_classes = (BaseJSONRenderer,)

    def post(self, request):
        user = request.user
        user.is_subscribed = True
        user.save()
        data = {
            'username': request.user.username
        }
        send_email(
            template='email_subscribe.html',
            data=data,
            to_email=request.user.email,
            subject='Email subscription activated',
        )
        res_data = {
            "message": {
                "subscription_status": request.user.is_subscribed,
                "message": "You have successfully subscribed to our notifications.",
            }
         }
        return Response(res_data, status=status.HTTP_200_OK)

    def delete(self, request):
        user = request.user
        user.is_subscribed = False
        user.save()
        data = {
            'username': request.user.username,
        }
        send_email(
            template='unsubscribe_email.html',
            data=data,
            to_email=request.user.email,
            subject='Email subscription deactivated',
        )
        res_data = {
            "message": {
                "subscription_status": request.user.is_subscribed,
                "message": "You have successfully unsubscribed from our notifications.",
            }
        }
        return Response(res_data, status=status.HTTP_200_OK)

class SubscriptionStatusAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    renderer_classes = (BaseJSONRenderer,)

    def get(self, request):
        res_data = {
            "subscription_status" : request.user.is_subscribed
        }
        return Response(res_data, status=status.HTTP_200_OK)
