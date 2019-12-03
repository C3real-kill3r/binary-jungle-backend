from rest_framework import serializers
from .models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializes and deserializes Profile instances.
    """
    # Fields from the user model
    username = serializers.CharField(source='user.username', read_only=True)
    # Profile specific fields
    bio = serializers.CharField()
    image = serializers.ImageField(default=None)

    class Meta:
        model = Profile
        fields = ['username', 'bio', 'image']
