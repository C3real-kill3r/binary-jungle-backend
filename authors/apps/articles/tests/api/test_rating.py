from rest_framework import status
from rest_framework.reverse import reverse

from authors.apps.articles.tests.api.test_articles import BaseArticlesTestCase


class TestArticleRating(BaseArticlesTestCase):

    def setUp(self):
        super().setUp()
        self.register()
        self.articleRating = {
            "rating": {
                "rating": 3
            }
        }
        self.bad_Rating = {
            "rating": {
                "rating": 7
            }
        }
        self.rating_user = {
            "user": {
                "username": "emily",
                "email": "emily@gmail.com",
                "password": "password1U@#}"
            }
        }

    def test_user_can_rate_available_article(self):
        """
        User who can rate article has to be authenticated
        """
        slug = self.create_article()['slug']
        rating = self.articleRating
        self.register_and_login(self.rating_user)
        response = self.client.put(reverse("articles:rate-article", kwargs={'slug': slug}), data=rating, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(b"You have successfully rated this article", response.content)

    def test_user_cannot_rate_unavailable_article(self):
        """
        If article does not exist, user cannot rate it
        """
        slug = "None"
        rating = self.articleRating
        self.register_and_login(self.rating_user)
        response = self.client.put(reverse("articles:rate-article", kwargs={'slug': slug}), data=rating, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn(b"This article does not exist!", response.content)

    def test_author_cannot_rate_his_articles(self):
        """
        Writers of articles cannot rate their own articles
        Their articles are rated by other users instead
        """
        slug = self.create_article()['slug']
        rating = self.articleRating
        response = self.client.put(reverse("articles:rate-article", kwargs={'slug': slug}), data=rating, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


    def test_user_can_rate_more_than_one(self):
        """
        Users should not rate articles more than once
        Instead they can edit ratings
        """
        slug = self.create_article()['slug']
        rating = self.articleRating
        self.register_and_login(self.rating_user)
        response = self.client.put(reverse("articles:rate-article", kwargs={'slug': slug}), data=rating, format="json")
        response = self.client.put(reverse("articles:rate-article", kwargs={'slug': slug}), data=rating, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_non_authenticated_user_cannot_rate_article(self):
        """
        For a user to rate an article, they have to be authenticated
        """
        slug = self.create_article()['slug']
        rating = self.articleRating
        self.logout()
        response = self.client.put(reverse("articles:rate-article", kwargs={'slug': slug}), data=rating, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_rating_should_be_between_one_and_five(self):
        """
        Rating should be in a range between one and five
        """
        slug = self.create_article()['slug']
        rating = self.bad_Rating
        self.register_and_login(self.rating_user)
        response = self.client.put(reverse("articles:rate-article", kwargs={'slug': slug}), data=rating, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(b"Rating should be a number between 1 and 5!", response.content)

    def test_rating_can_be_upated(self):
        """
        If a user can update existing rating on article
        """
        slug = self.create_article()['slug']
        rating = self.articleRating
        self.register_and_login(self.rating_user)
        response = self.client.put(reverse("articles:rate-article", kwargs={'slug': slug}), data=rating, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_user_cannot_edit_nonexisting_article_rating(self):
        """
        If a user had not previously rated an article, they cannot edit the rating
        """
        slug = None
        rating = self.articleRating
        self.register_and_login(self.rating_user)
        response = self.client.put(reverse("articles:rate-article", kwargs={'slug': slug}), data=rating, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn(b"This article does not exist!", response.content)


    def test_user_cannot_get_rate_unavailable_article(self):
        """
        If article does not exist, user cannot get article rating
        """
        slug = "None"
        self.register_and_login(self.rating_user)
        response = self.client.get(reverse("articles:rate-article", kwargs={'slug': slug}), format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn(b"This article does not exist!", response.content)

    def test_user_cannot_get_from_unavailable_article(self):
        """
        If article does not exist, user cannot get all rating
        """
        slug = "None"
        rating = self.articleRating
        self.register_and_login(self.rating_user)
        response = self.client.get(reverse("articles:rating-article", kwargs={'slug': slug}),format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn(b"This article does not exist!", response.content)


    def test_user_cannot_rate_unavailable_article(self):
        """
        If article does not exist, user cannot rate it
        """
        slug = "None"
        rating = self.articleRating
        self.register_and_login(self.rating_user)
        response = self.client.get(reverse("articles:rating-article", kwargs={'slug': slug}), data=rating, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_rating_get(self):
        """
        If a user can get existing rating on article
        """
        slug = self.create_article()['slug']
        self.register_and_login(self.rating_user)
        response = self.client.get(reverse("articles:rate-article", kwargs={'slug': slug}), format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)



    def test_rating_get_all_rating(self):
        """
        If a user can update existing rating on article
        """
        slug = self.create_article()['slug']
        self.register_and_login(self.rating_user)
        response = self.client.get(reverse("articles:rating-article", kwargs={'slug': slug}), format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
