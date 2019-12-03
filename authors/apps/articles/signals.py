from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from authors.apps.ah_notifications.notifications import Verbs
from authors.apps.core.mail_sender import send_email
from notifications.signals import notify
from rest_framework.reverse import reverse

from authors.apps.articles.models import Article, FavouriteArticle, Comment


@receiver(post_save, sender=Article)
def send_create_article_notification_to_followers(sender, instance, created, **kwargs):
    followers = instance.author.profile.followers()

    for follower in followers:
        if follower.user.is_subscribed:
            data = {
                'username': follower.user.username,
                'article_title': instance.title,
                'author': instance.author.username,
                'unsubscribe_url': 'http://localhost:8000'+reverse('notifications:subscribe')
            }
            send_email(
                template='article_created.html',
                data=data,
                to_email=follower.user.email,
                subject='You have a new notification',
            )
        notify.send(instance, verb=Verbs.ARTICLE_CREATION, recipient=follower.user,
                    description="An article by an author you follow has been created")


@receiver(post_save, sender=FavouriteArticle)
def send_user_favorited_article_to_author(sender, instance, created, **kwargs):
    notify.send(instance, verb=Verbs.ARTICLE_FAVORITING, recipient=instance.article.author,
                description="{} just favorited your article".format(instance.user.email))


@receiver(post_save, sender=Comment)
def send_user_commented_on_article_to_author(sender, instance, created, **kwargs):
    notify.send(instance, verb=Verbs.ARTICLE_COMMENT, recipient=instance.article.author,
                description="{} commented on \"{}\"".format(instance.author.username, instance.article.title))
