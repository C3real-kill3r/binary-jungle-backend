from django.db import models

from authors.apps.core.models import TimestampsMixin
from authors.settings import AUTH_USER_MODEL
from cloudinary.models import CloudinaryField

from notifications.signals import notify
from authors.apps.ah_notifications.notifications import Verbs


class FollowMixin(models.Model):
    """
    This mixin adds follow-un follow logic to the user profile.
    """
    # symmetrical is set to False to prevent creation of reverse follow i.e. if it was not
    # set to False, if profile A followed profile B, a relationship would also be
    # created with profile B following A.
    follows = models.ManyToManyField('self', related_name='followed_by', symmetrical=False)

    def follow(self, profile):
        """
        Follow a profile.
        :param profile: Profile
        """
        notify.send(self, verb=Verbs.USER_FOLLOWING, recipient=profile.user, 
                    description="{} has just followed you!".format(self.username))
        return self.follows.add(profile)

    def un_follow(self, profile):
        """
        Un-follow a profile.
        :param profile: Profile.
        """
        return self.follows.remove(profile)

    def followers(self):
        """
        Get a list of profiles that follow this profile.
        """
        return self.followed_by.all()

    def following(self):
        """
        Get a list of profiles that this profile follows.
        """
        return self.follows.all()

    class Meta:
        abstract = True


class Profile(TimestampsMixin, FollowMixin):
    """
    This model creates a user profile with bio and
    image field once a user creates an account.
    """
    user = models.OneToOneField(AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    bio = models.TextField(default="Update your bio description")
    image = CloudinaryField('image')

    @property
    def username(self):
        return self.user.username

    def __str__(self):
        return self.user.username
