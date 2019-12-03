import json
import random
import string

from rest_framework import status
from rest_framework.reverse import reverse

from authors.apps.articles.tests.api.test_articles import BaseArticlesTestCase


class BaseTagsTestCase(BaseArticlesTestCase):

    def setUp(self):
        super().setUp()
        self.tags = {
            "tags": [
                "Andela",
                "Cohort 30",
                "MacBook Pro 2016"
            ]
        }
        # create an article
        self.article_slug = self.create_article(published=True)['slug']

    def generate_url(self, slug):
        """
        Generate tagging url for an article
        :param slug:
        :return:
        """
        return reverse("articles:article-tags", kwargs={'slug': slug or self.article_slug})

    def tag_article(self, slug=None, tags=None):
        """
        Helper method to tag an article
        :param slug:
        :param tags:
        :return:
        """
        return self.client.post(self.generate_url(slug), tags or self.tags, format="json")

    def un_tag_article(self, slug=None, tags=None):
        """
        Helper method to remove tags from an article
        :param slug:
        :param tags:
        :return:
        """
        return self.client.delete(self.generate_url(slug), tags or self.tags, format="json")

    def list_tags(self, slug=None):
        """
        Helper method to get the tags for a particular article
        :param slug:
        :return:
        """
        return self.client.get(self.generate_url(slug))


class TagCreationTestCase(BaseTagsTestCase):

    def test_user_can_tag_article(self):
        """
        Make sure a user can add tags to their own article
        :return:
        """
        response = self.tag_article()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        slug = json.loads(response.content)['data']['article']
        tags = json.loads(response.content)['data']['tags']
        for tag in self.tags['tags']:
            self.assertIn(tag, tags)
        self.assertEqual(slug, self.article_slug)

    def test_unauthenticated_user_cannot_tag_article(self):
        """
        Ensure an unauthenticated user cannot tag an article
        :return:
        """
        self.logout()
        response = self.tag_article()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_another_only_owner_can_tag_article(self):
        """
        Ensure only the owner of the article can add tags to it
        :return:
        """
        self.register_and_login(self.user2)
        response = self.tag_article()

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_tags_cannot_be_duplicated(self):
        """
        Ensure the tags are not duplicated when they are created
        :return:
        """
        self.tag_article()
        response = self.tag_article()
        tags = json.loads(response.content)['data']['tags']
        for tag in self.tags['tags']:
            # ensure each tag appears only once
            self.assertEqual(tags.count(tag), 1)

    def test_tag_name_cannot_be_empty(self):
        """
        Ensure the name of the tag cannot be empty
        :return:
        """
        self.tags['tags'].append("")
        response = self.tag_article()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(b'Please specify a tag', response.content)

    def test_tag_name_cannot_be_more_than_28_characters(self):
        """
        Ensure the name of a tag cannot be more than 28 characters
        :return:
        """
        self.tags["tags"].append(string.ascii_lowercase + string.ascii_lowercase)
        response = self.tag_article()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(b'Tag cannot be more than 28 characters', response.content)


class TagRemovalTestCase(BaseTagsTestCase):

    def setUp(self):
        super().setUp()
        self.article_tags = self.tag_article()

    def tag_article(self, slug=None, tags=None):
        """
        Overridden method in order to return the tags of an article after tagging
        :param slug:
        :param tags:
        :return:
        """
        response = super().tag_article(slug, tags)
        return json.loads(response.content)['data']['tags']

    def test_user_can_remove_tags_from_an_article(self):
        """
        Ensure a user can remove tags from an article
        :return:
        """
        response = self.un_tag_article()
        tags = json.loads(response.content)['data']['tags']

        for tag in self.tags:
            # check that the tags do not exist after being removed
            self.assertNotIn(tag, tags)

    def test_unauthenticated_user_cannot_remove_tags(self):
        """
        Ensure a user that is not authenticated cannot remove tags from an article
        :return:
        """
        self.logout()
        response = self.un_tag_article()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_only_owner_can_remove_tags_from_an_article(self):
        """
        Ensure other users cannot un_tag an article
        :return:
        """
        self.register_and_login(self.user2)
        response = self.un_tag_article()

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TagRetrievalTestCase(BaseTagsTestCase):
    TOTAL_NUM_TAGS = 6

    def setUp(self):
        super().setUp()
        # tag an article
        self.tag_article()

    def test_owner_can_view_tags_on_their_published_articles(self):
        """
        Ensure the owner can view tags on their published articles
        :return:
        """
        response = self.list_tags()
        tags = json.loads(response.content)['data']['tags']

        self.assertEqual(len(tags), self.TOTAL_NUM_TAGS)

    def test_owner_can_view_tags_on_their_unpublished_articles(self):
        """
        Ensure the owner can also view tags on their unpublished articles
        :return:
        """
        slug = self.create_article(published=False)['slug']
        self.tag_article(slug=slug)
        response = self.list_tags(slug=slug)

        tags = json.loads(response.content)['data']['tags']
        self.assertEqual(len(tags), self.TOTAL_NUM_TAGS)

    def test_unauthenticated_user_can_view_tags_on_published_articles(self):
        """
        Ensure an unauthenticated user can view tags on published articles
        :return:
        """
        self.logout()
        response = self.list_tags()
        tags = json.loads(response.content)['data']['tags']
        self.assertEqual(len(tags), self.TOTAL_NUM_TAGS)

    def test_unauthenticated_user_cannot_view_tags_on_unpublished_articles(self):
        """
        Ensure an unauthenticated user cannot view tags on unpublished articles
        :return:
        """
        slug = self.create_article(published=False)['slug']
        self.tag_article(slug=slug)

        # logout user
        self.logout()
        response = self.list_tags(slug=slug)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_another_user_can_view_tags_on_published_articles(self):
        """
        Ensure another authenticated user can view tags on published articles
        :return:
        """
        self.register_and_login(self.user2)
        response = self.list_tags()

        tags = json.loads(response.content)['data']['tags']
        self.assertEqual(len(tags), self.TOTAL_NUM_TAGS)

    def test_another_user_cannot_view_tags_on_unpublished_articles(self):
        """
        Ensure another authenticated user cannot view tags on unpublished articles
        :return:
        """

        slug = self.create_article(published=False)['slug']
        self.tag_article(slug=slug)

        # logout user
        self.register_and_login(self.user2)
        response = self.list_tags(slug=slug)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_can_get_all_tags(self):
        """
        Ensure all tags can be retrieved
        :return:
        """
        response = self.client.get(reverse("tags"))
        tags = json.loads(response.content)['data']['tags']
        self.assertEqual(len(tags), self.TOTAL_NUM_TAGS)
