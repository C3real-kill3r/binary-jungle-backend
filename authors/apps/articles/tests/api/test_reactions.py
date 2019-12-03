from django.urls import reverse
from rest_framework import status

from authors.apps.articles.models import Article
from authors.apps.articles.tests.api.test_articles import BaseArticlesTestCase
from authors.apps.core.test_helpers import set_test_client, login, logout


class BaseReactionsTestCase(BaseArticlesTestCase):
    def setUp(self):
        super().setUp()
        set_test_client(self.client)
        self.slug = self.generate_article()
        logout()

    # like helpers
    def like_url(self, slug):
        return reverse('articles:like', kwargs={'slug': slug})

    def like(self, slug):
        return self.client.post(self.like_url(slug=slug))

    def un_like(self, slug):
        return self.client.delete(self.like_url(slug=slug))

    # dislike helpers
    def dislike_url(self, slug):
        return reverse('articles:dislike', kwargs={'slug': slug})

    def dislike(self, slug):
        return self.client.post(self.dislike_url(slug=slug))

    def un_dislike(self, slug):
        return self.client.delete(self.dislike_url(slug=slug))

    # reaction helpers
    def get_reactions(self, slug):
        return self.client.get(reverse('articles:reactions', kwargs={'slug': slug}))

    def assertReactionsEqual(self, reactions, like_count=0, like_me=False, dislike_count=0, dislike_me=False):
        """
        Asserts that the passed reactions dictionary's fields
        are equal to those supplied by the other arguments.
        :param reactions: dict
        :param like_count: int
        :param like_me: bool
        :param dislike_count: int
        :param dislike_me: bool
        """
        self.assertEqual(reactions, {
            'likes': {
                'count': like_count,
                'me': like_me
            },
            'dislikes': {
                'count': dislike_count,
                'me': dislike_me
            }
        })

    def generate_article(self, field='slug', return_obj=False):
        """
        Creates an article and returns the field specified by the field
        argument. If return_obj is set to True is returns the created
        article object instead of the specified field.
        :param field:
        :param return_obj:
        :return:
        """
        article = self.create_article()

        if return_obj:
            return Article.objects.get(slug=article['slug'])

        return article[field]


class ReactionsTestCase(BaseReactionsTestCase):
    def setUp(self):
        super().setUp()

    def test_users_can_get_reactions(self):
        response = self.get_reactions(self.slug)
        self.assertReactionsEqual(response.data['reactions'])

    def test_like_count_is_accurate(self):
        login()
        self.like(self.slug)
        login()
        self.like(self.slug)
        login()
        response = self.get_reactions(self.slug)
        self.assertReactionsEqual(response.data['reactions'], like_count=2)

    def test_dislike_count_is_accurate(self):
        login()
        self.dislike(self.slug)
        login()
        self.dislike(self.slug)
        login()
        response = self.get_reactions(self.slug)
        self.assertReactionsEqual(response.data['reactions'], dislike_count=2)

    def test_like_me_is_accurate(self):
        login()
        self.like(self.slug)
        response = self.get_reactions(self.slug)
        self.assertReactionsEqual(response.data['reactions'], like_me=True, like_count=1)

    def test_dislike_me_is_accurate(self):
        login()
        self.dislike(self.slug)
        response = self.get_reactions(self.slug)
        self.assertReactionsEqual(response.data['reactions'], dislike_me=True, dislike_count=1)


class LikeTestCase(BaseReactionsTestCase):
    def setUp(self):
        super().setUp()

    def test_users_can_like_article(self):
        login()
        response = self.like(self.slug)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], 'You like this article.')

    def test_an_article_can_have_many_likes(self):
        login()
        self.like(self.slug)  # first like
        login()
        response = self.like(self.slug)  # second like
        self.assertReactionsEqual(response.data['reactions'], like_count=2, like_me=True)

    def test_unauthenticated_users_cannot_like_articles(self):
        response = self.like(self.slug)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_users_can_un_like_articles(self):
        login()
        response = self.un_like(self.slug)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'You no longer like this article.')

    def test_unauthenticated_users_cannot_un_like_articles(self):
        response = self.un_like(self.slug)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_liking_an_article_reverts_a_dislike_on_it(self):
        login()
        response = self.dislike(self.slug)  # dislike
        self.assertReactionsEqual(
            response.data['reactions'],
            like_count=0, like_me=False, dislike_count=1, dislike_me=True
        )
        response = self.like(self.slug)  # like
        self.assertReactionsEqual(
            response.data['reactions'],
            like_count=1, like_me=True, dislike_count=0, dislike_me=False
        )


class DislikeTestCase(BaseReactionsTestCase):
    def setUp(self):
        super().setUp()

    def test_users_can_dislike_article(self):
        login()
        response = self.dislike(self.slug)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], 'You dislike this article.')

    def test_an_article_can_have_many_dislikes(self):
        login()
        self.dislike(self.slug)  # first dislike
        login()
        response = self.dislike(self.slug)  # second dislike
        self.assertReactionsEqual(response.data['reactions'], dislike_count=2, dislike_me=True)

    def test_unauthenticated_users_cannot_dislike_articles(self):
        response = self.dislike(self.slug)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_users_can_un_dislike_article(self):
        login()
        response = self.un_dislike(self.slug)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'You no longer dislike this article.')

    def test_unauthenticated_users_cannot_un_dislike_articles(self):
        response = self.un_dislike(self.slug)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_disliking_an_article_reverts_a_like_on_it(self):
        login()
        response = self.like(self.slug)  # like
        self.assertReactionsEqual(
            response.data['reactions'],
            like_count=1, like_me=True, dislike_count=0, dislike_me=False
        )
        response = self.dislike(self.slug)  # dislike
        self.assertReactionsEqual(
            response.data['reactions'],
            like_count=0, like_me=False, dislike_count=1, dislike_me=True
        )
