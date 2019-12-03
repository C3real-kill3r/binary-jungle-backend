from django.urls import path

from .views import (
    AllNotificationsAPIView,
    UnreadNotificationsAPIView,
    ReadNotificationsAPIView,
    UnsentNotificationsAPIView,
    SentNotificationsAPIView,
    SubscribeAPIView,
    SubscriptionStatusAPIView,
    )


app_name = "notifications"

urlpatterns = [
    path('all/', AllNotificationsAPIView.as_view(), name="notifications"),
    path('unread/', UnreadNotificationsAPIView.as_view(), name="unread-notifications"),
    path('read/', ReadNotificationsAPIView.as_view(), name="read-notifications"),
    path('read/<int:pk>/', ReadNotificationsAPIView.as_view(), name="read-notification"),
    path('unsent/', UnsentNotificationsAPIView.as_view(), name="unsent-notifications"),
    path('sent/', SentNotificationsAPIView.as_view(), name="sent-notifications"),
    path('subscribe/', SubscribeAPIView.as_view(), name="subscribe"),
    path('subscription-status/', SubscriptionStatusAPIView.as_view(), name="subscription-status")
]
