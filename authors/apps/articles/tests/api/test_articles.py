import json
import random
import string

from django.utils.text import slugify
from rest_framework import status
from rest_framework.reverse import reverse

from authors.apps.authentication.tests.api.test_auth import AuthenticatedTestCase


class BaseArticlesTestCase(AuthenticatedTestCase):
    DEFAULT_NUM_ARTICLES = 10  # Default number of articles to be randomly created
    """
    Extend this class in order to use the articles functionality
    """

    def setUp(self):
        super().setUp()
        self.article = {
            "article": {
                "title": "How to train your dragon today",
                "description": "Ever wonder how?",
                "body": "You have to believe in you",
                "tags": [
                    "reactjs",
                    "angularjs",
                    "dragons"
                ],
                "image": "https://dummyimage.com/600x400/000/fff",
                "published": False
            }
        }
        self.url_list = reverse("articles:articles-list")
        self.user2 = {
            "user": {
                "username": "gitaumoses4",
                "email": "gitaumoses40@gmail.com",
                "password": "passwordU1#@243"
            }
        }

    def create_random_articles(self):
        """
        Helper method to create a list of articles
        :return:
        """
        for x in range(0, self.DEFAULT_NUM_ARTICLES):
            # create a list of published an unpublished articles
            self.create_article(published=(x % 2 == 0))

    def create_30_articles(self):
        """
        Helper method to create a list of articles
        :return:
        """
        for x in range(0, 30):
            # create a list of published an unpublished articles
            self.create_article(published=(x % 2 == 0))

    def create_article(self, article=None, published=False):
        """
        Overridden method, it will return the data of the created article instead
        :param published: set the article as published
        :param article:
        :return:
        """

        if article is None:
            article = self.article
        article['article']['published'] = published
        response = self.client.post(self.url_list, data=article, format="json")
        return json.loads(response.content)['data']['article']

    def url_retrieve(self, slug):
        """
        Helper method to create the url to retrieve an article
        :param slug:
        :return:
        """
        return reverse("articles:articles-detail", kwargs={"slug": slug})


class CreateArticlesTestCase(BaseArticlesTestCase):
    """
    Test for the articles creation
    """

    def create_article(self, article=None, published=False):
        """
        Overridden method to return the response
        :param article:
        :param published:
        :return:
        """
        if article is None:
            article = self.article
        article['article']['published'] = published

        return self.client.post(self.url_list, data=article, format="json")

    def test_verified_user_can_create_article(self):
        """
        Ensure a verified user can create an article
        :return:
        """
        response = self.create_article()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_article_without_image(self):
        """
        Ensure that the readtime algorithm factors the presence/absence of an image
        """
        article = {
            "article": {
                "title": "How to train your dragon today",
                "description": "Ever wonder how?",
                "body": "You have to believe in you",
                "tags": [
                    "reactjs",
                    "angularjs",
                    "dragons"
                ],
                "published": False
            }
        }
        response = self.client.post(self.url_list, data=self.article, format="json")
        current_readtime = response.data["read_time"]
        res = self.client.post(self.url_list, data=article, format="json")
        updated_readtime = res.data["read_time"]
        self.assertEqual(current_readtime - updated_readtime, 10.0)

    def test_unverified_user_cannot_create_article(self):
        """
        Ensure an unverified user cannot create an article
        :return:
        """
        self.unverify_user()
        response = self.create_article()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_cannot_create_article_without_logging_in(self):
        """
        Ensure that a user has to login in order to create an article
        :return:
        """
        self.logout()
        response = self.create_article()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn(b"Authentication credentials were not provided.", response.content)

    def test_cannot_create_article_without_title(self):
        """
        Ensure that a user cannot create an article without a title
        :return:
        """
        self.article['article']['title'] = ''
        response = self.create_article()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(b'The article must have a title', response.content)

    def test_cannot_create_article_without_description(self):
        """
        Ensure that a user cannot create an article without a description
        :return:
        """
        self.article['article']['description'] = ''
        response = self.create_article()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(b"The article must have a description", response.content)

    def test_cannot_create_article_without_body(self):
        """
        Ensure the article must have a body, that is not empty
        :return:
        """
        self.article['article']['body'] = ''
        response = self.create_article()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(b'The article must have a body', response.content)

    def test_title_cannot_be_more_than_255_characters(self):
        """
        Ensure the title must be less than 255 characters
        :return:
        """
        self.article['article']['title'] = ''.join(
            random.choice(string.ascii_lowercase + string.ascii_uppercase) for _ in range(256))
        response = self.create_article()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(b'The article title cannot be more than 255 characters', response.content)

    def test_tags_must_be_a_list(self):
        """
        Ensure the list of tags will be passed in as a list of strings
        :return:
        """
        self.article['article']['tags'] = 'AngularJS'

        response = self.create_article()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(b"The tags must be a list of strings", response.content)

    def test_slug_made_from_title(self):
        """
        Ensure the slug is made from the title of the article
        :return:
        """
        response = self.create_article()
        self.assertIn(slugify(self.article['article']['title']),
                      json.loads(response.content)['data']['article']['slug'])


class GetArticlesTestCase(BaseArticlesTestCase):

    def get_all_articles(self):
        """
        Lists all the articles that have been created
        :return:
        """
        response = self.client.get(self.url_list, data=None, format="json")
        return json.loads(response.content)['data']['article']

    def get_single_article(self, slug):
        """
        Get an article by slug
        :return:
        """
        return self.client.get(self.url_retrieve(slug), data=None, format="json")

    def test_user_can_get_created_article(self):
        """
        Ensure the user get an article they created, this tests whether the user can get an unpublished article they
        created
        :return:
        """
        slug = self.create_article()['slug']
        response = self.get_single_article(slug)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(str.encode(slug), response.content)

    def test_article_has_share_links(self):
        """
        Ensures the user can be able to share an article through social media
        platforms like Twitter, Facebook, LinkedIn or mail
        """
        slug = self.create_article()['slug']
        res = self.get_single_article(slug)
        self.assertIn('share_article', res.data)
        self.assertIn('Facebook', res.data['share_article'])
        self.assertIn('Twitter', res.data['share_article'])
        self.assertIn('LinkedIn', res.data['share_article'])
        self.assertIn('Email', res.data['share_article'])

    def test_article_has_read_time(self):
        """
        Ensure the articles have a readtime property
        :return:
        """
        slug = self.create_article()['slug']
        response = self.get_single_article(slug)
        self.assertIn(b'read_time', response.content)
        self.assertIsInstance(response.data["read_time"], float)

    def test_another_user_cannot_get_unpublished_article(self):
        """
        Ensure another user cannot view an article that has not been published by other users
        :return:
        """
        # let the first user create the article, by default it is always not published
        slug = self.create_article()['slug']

        # register and login another user
        self.register_and_login(self.user2)
        # try to get the article
        response = self.get_single_article(slug)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_another_user_can_get_published_article(self):
        """
        Ensure a user can get a published article for another user
        :return:
        """
        slug = self.create_article(published=True)['slug']

        # register and login another user
        self.register_and_login(self.user2)

        # try to get article
        response = self.get_single_article(slug)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(str.encode(slug), response.content)

    def test_unauthenticated_user_cannot_get_unpublished_article(self):
        """
        Ensure an unauthenticated user cannot get a article that is not published
        :return:
        """
        slug = self.create_article()['slug']

        # lgoout user
        self.logout()

        # try as unauthenticated user
        response = self.get_single_article(slug)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_user_can_get_published_article(self):
        """
        Ensure an unauthenticated user can get an article that is published
        :return:
        """
        slug = self.create_article(published=True)['slug']

        # logout user
        self.logout()

        # try as unauthenticated user
        response = self.get_single_article(slug)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(str.encode(slug), response.content)

    def test_creator_can_list_all_published_and_unpublished_articles(self):
        """
        Ensure the list contains only published articles
        :return:
        """
        self.create_random_articles()
        response = self.get_all_articles()
        # ensure all five articles are visible
        self.assertEqual(self.DEFAULT_NUM_ARTICLES, response['count'])

    def test_other_user_can_only_see_published_articles(self):
        """
        Ensure other users can only see the published articles
        :return:
        """
        self.create_random_articles()

        self.register_and_login(self.user2)  # login another user

        articles = self.get_all_articles()
        for article in articles['results']:
            self.assertTrue(article['published'])

    def test_unauthenticated_user_can_only_see_published_articles(self):
        """
        Ensure unauthenticated users cannot see unpublished articles
        :return:
        """
        self.create_random_articles()

        self.logout()

        articles = self.get_all_articles()
        for article in articles['results']:
            self.assertTrue(article['published'])

    def test_user_cannot_get_404_article(self):
        """
        Ensure the correct message is given for an article that does not exist
        :return:
        """
        # create a fake slug
        slug = self.create_article()['slug'] + ''.join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase) for _ in range(5))

        response = self.get_single_article(slug)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_api_returns_paginated_articles(self):
        """
        Ensure API returns paginated articles
        """
        self.create_random_articles()
        res = self.get_all_articles()
        self.assertIn('count', res.keys())
        self.assertIn('links', res.keys())
        self.assertIn('total_pages', res.keys())

    def test_user_can_query_articles_using_page_numbers(self):
        """
        Ensures a user can query articles using page numbers
        """
        self.create_30_articles()
        res = self.client.get(self.url_list + '?page=2', data=None, format="json")
        self.assertEqual(10, len(res.data['results']))
        self.assertIsNone(res.data['links']['next'])
        self.assertIsNotNone(res.data['links']['previous'])

    def test_user_can_query_articles_using_page_size(self):
        """
        Ensures a user can query articles using page size
        """
        self.create_30_articles()
        res = self.client.get(self.url_list + '?page_size=2', data=None, format="json")
        self.assertEqual(2, len(res.data['results']))
        self.assertIsNone(res.data['links']['previous'])
        self.assertIsNotNone(res.data['links']['next'])

    def test_user_can_query_articles_using_page_size_and_page_number(self):
        """
        Ensures a user can query articles using page numbers
        and page size
        """
        self.create_30_articles()
        res = self.client.get(self.url_list + '?page_size=2', data=None, format="json")
        self.assertEqual(2, len(res.data['results']))
        self.assertIsNone(res.data['links']['previous'])
        self.assertIsNotNone(res.data['links']['next'])


class UpdateArticleTestCase(BaseArticlesTestCase):

    def update_article(self, article, slug):
        """
        Helper method to update the details of an article
        :param article:
        :param slug:
        :return:
        """
        return self.client.put(self.url_retrieve(slug), data=article, format="json")

    def test_can_update_article_title(self):
        """
        Check that the title of the article can be updated
        :return:
        """
        slug = self.create_article()['slug']

        self.article['article']['title'] = "This is a new title"
        response = self.update_article(self.article, slug=slug)
        # ensure the titles are similar
        self.assertIn(str.encode(self.article['article']['title']), response.content)

    def test_slug_changes_for_unpublished_article(self):
        """
        Whenever the title of an unpublished article changes, the slug should change too
        :return:
        """
        slug = self.create_article()['slug']

        self.article['article']['title'] = "This is a new title"
        response = self.update_article(self.article, slug)

        # ensure the slug changed
        self.assertNotEqual(json.loads(response.content)['data']['article']['slug'], slug)

    def test_slug_does_not_change_for_published_article(self):
        """
        The slug should not change for published articles to avoid broken links when users share the links
        :return:
        """

        slug = self.create_article(published=True)['slug']

        self.article['article']['title'] = "This is a new title"
        response = self.update_article(self.article, slug)

        # ensure the slug changed
        self.assertEqual(json.loads(response.content)['data']['article']['slug'], slug)

    def test_user_can_update_article_description(self):
        """
        Ensure the description of the article can be changed
        :return:
        """

        slug = self.create_article()['slug']

        self.article['article']['description'] = "This is a new description"
        response = self.update_article(self.article, slug=slug)

        self.assertIn(str.encode(self.article['article']['description']), response.content)

    def test_user_can_update_article_body(self):
        """
        Ensure the body of the article can be updated
        :return:
        """

        slug = self.create_article()['slug']

        self.article['article']['body'] = "This is a new article body"
        response = self.update_article(self.article, slug=slug)

        self.assertIn(str.encode(self.article['article']['body']), response.content)

    def test_a_user_cannot_edit_an_article_that_does_not_belong_to_them(self):
        """
        Ensure that a user cannot edit an article that does not belong to them
        :return:
        """
        slug = self.create_article()['slug']

        # login another user
        self.register_and_login(self.user2)

        response = self.update_article(self.article, slug=slug)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_cannot_edit_an_article(self):
        """
        Ensure that a user that is not authenticated cannot modify an article
        :return:
        """
        slug = self.create_article()['slug']

        # logout user
        self.logout()

        response = self.update_article(self.article, slug=slug)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_can_change_tags(self):
        """
        Ensure the user can change the tags for an article
        :return:
        """
        slug = self.create_article()['slug']

        self.article['article']['tags'] = ['this', 'are', 'some', 'new', 'tags']
        response = self.update_article(self.article, slug=slug)

        # check for similarity
        for x in json.loads(response.content)['data']['article']['tags']:
            self.assertIn(x, self.article['article']['tags'])

    def test_cannot_update_details_for_non_existing_article(self):
        """
        Ensure a user cannot update the details of a article that does not exist
        :return:
        """
        slug = self.create_article()['slug'] + ''.join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase) for _ in range(5))

        response = self.update_article(self.article, slug)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_change_article_image(self):
        """
        Ensure the user can update the image of the article
        :return:
        """

        slug = self.create_article()['slug']
        self.article['article']['image'] = "Https://google.com/images/this-is-a-new-image.jpg"

        response = self.update_article(self.article, slug=slug)
        self.assertEqual(json.loads(response.content)['data']['article']['image'], self.article['article']['image'])


class DeleteArticleTestCase(BaseArticlesTestCase):
    """
    Test for deletion method of the articles
    """

    def delete_article(self, slug):
        """
        Helper method to delete articles
        :param slug:
        :return:
        """
        return self.client.delete(self.url_retrieve(slug), data=None, format="json")

    def test_owner_can_delete_article(self):
        """
        Ensure the owner can delete an article
        :return:
        """
        slug = self.create_article()['slug']

        response = self.delete_article(slug)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b'The article has been deleted', response.content)

    def test_cannot_delete_an_article_that_does_not_exist(self):
        """
        Ensure the current status is returned when deleting an article that does not exist
        :return:
        """
        slug = self.create_article()['slug']
        self.delete_article(slug)

        response = self.delete_article(slug)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_cannot_delete_article_that_does_not_belong_to_them(self):
        """
        Ensure the user is prevented from deleting an article they do not own
        :return:
        """

        slug = self.create_article()['slug']

        # switch to another user
        self.register_and_login(self.user2)

        response = self.delete_article(slug)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_cannot_delete_article(self):
        """
        Ensure that a user that is not authenticated cannot delete an article
        :return:
        """
        slug = self.create_article()['slug']

        # logout the user

        self.logout()

        response = self.delete_article(slug)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
