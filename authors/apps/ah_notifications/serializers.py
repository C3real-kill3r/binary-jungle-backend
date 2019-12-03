from notifications.models import Notification
from rest_framework import serializers

from authors.apps.articles.models import Article, Comment
from authors.apps.articles.serializers import CommentSerializer
from authors.apps.authentication.models import User
from authors.apps.profiles.models import Profile
from authors.apps.profiles.serializers import ProfileSerializer


class ActorField(serializers.RelatedField):
    """
    To represent an actor that triggers the notification,

    A comment is represented
    """

    def to_representation(self, value):
        actor_type = None
        data = []
        if isinstance(value, Article):
            actor_type = "article"
            data = {"slug": value.slug}
        elif isinstance(value, Comment):
            actor_type = "comment"
            data = CommentSerializer(value).data
        elif isinstance(value, User):
            actor_type = "user"
            data = ProfileSerializer(Profile.objects.get(user=value)).data

        return {
            "type": actor_type,
            "data": data
        }

    def to_internal_value(self, data):
        return Notification(data)


class NotificationSerializer(serializers.ModelSerializer):
    actor = ActorField(read_only=True)
    target = ActorField(read_only=True)

    class Meta:
        model = Notification

        fields = ('id', 'actor', 'verb', 'target', 'level', 'unread', 'timestamp', 'description',)
