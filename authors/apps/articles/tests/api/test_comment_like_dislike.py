from rest_framework import status
from rest_framework.reverse import reverse
from authors.apps.articles.tests.api.test_articles import BaseArticlesTestCase
import json


class TestCommentLikeDislike(BaseArticlesTestCase):
    """This class tests for like and dislike of article"""

    def setUp(self):
        super().setUp()
        self.register()
        self.slug = self.create_article()['slug']
        self.comment = {"comment": {"body": "comment on this "}}
        self.thread = {"comment": {"body": "comment on this thread "}}
        response = self.client.post(
            reverse("articles:comments", kwargs={'slug': self.slug}),
            data=self.comment,
            format="json")
        self.pk = json.loads(response.content)["data"]['comment']['id']
        self.user = {
            "user": {
                "username": "tester001",
                "email": "test@example.com",
                "password": "@Asecret123"
            }
        }

    # like helpers
    def like_url(self, slug, pk):
        return reverse('articles:likes', kwargs={'slug': slug, "pk": pk})

    def dislike_url(self, slug, pk):
        return reverse('articles:dislikes', kwargs={'slug': slug, "pk": pk})

    def like(self, slug, pk):
        return self.client.put(self.like_url(slug=slug, pk=pk))

    def dislike(self, slug, pk):
        return self.client.put(self.dislike_url(slug=slug, pk=pk))

    def test_user_can_like_comment(self):
        """Test like a comment"""
        self.register_and_login(self.user)
        response = self.dislike(self.slug, self.pk)
        response = self.like(self.slug, self.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unlike_comment(self):
        """Test unlike comment updating twice """
        self.register_and_login(self.user)
        response = self.like(self.slug, self.pk)
        response = self.dislike(self.slug, self.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_like_nonexisting_artilce_comment(self):
        """Test incorret slug in liking"""
        self.register_and_login(self.user)
        response = self.dislike("fakeslug", self.pk)
        response = self.like("fakeslug", self.pk)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_like_nonexisting_pk_comment(self):
        """Test incorrect pk in liking"""
        self.register_and_login(self.user)
        response = self.dislike(self.slug, 2)
        response = self.like(self.slug, 2)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_dislike_comment(self):
        """Test like a comment"""
        self.register_and_login(self.user)
        response = self.dislike(self.slug, self.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unlike_dislike_comment(self):
        """Test unlike comment updating twice """
        self.register_and_login(self.user)
        response = self.dislike(self.slug, self.pk)
        response = self.dislike(self.slug, self.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_dislike_nonexisting_artilce_comment(self):
        """Test incorret slug in liking"""
        self.register_and_login(self.user)
        response = self.dislike("fakeslug", self.pk)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_disike_nonexisting_pk_comment(self):
        """Test incorrect pk in liking"""
        self.register_and_login(self.user)
        response = self.dislike(self.slug, 3)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
