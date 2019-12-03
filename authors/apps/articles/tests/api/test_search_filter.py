import json

from rest_framework.reverse import reverse

from authors.apps.articles.tests.api.test_articles import BaseArticlesTestCase

true = True
false = False


class TestFavouriteArticle(BaseArticlesTestCase):
    """Base class to use for testing search and filter functionalities"""

    def setUp(self):
        super().setUp()
        self.register()
        self.article1 = {"article": {
            "title": "with real mango",
            "tags": ["foods", "ryb", "andela"],
            "published": true}}
        self.article2 = {"article": {
            "title": "greatest",
            "description": "never hot blah",
            "body": "kevin is a boy",
            "tags": ["brian", "ryb", "bev"],
            "published": true}}
        self.article3 = {"article": {
            "title": "never",
            "description": "who runs the world",
            "body": "I love it more",
            "tags": ["brian", "shoe", "book"],
            "published": false}}

    def create_articles(self):
        self.url_article = reverse("articles:articles-list")
        article = self.article1
        article2 = self.article2
        article3 = self.article3
        self.client.post(self.url_article, data=article, format="json")
        self.client.post(self.url_article, data=article2, format="json")
        self.client.post(self.url_article, data=article3, format="json")
        articles = self.client.get(self.url_article, format="json")
        return articles

    def test_user_can_filter_article_using_tag(self):
        """any user(authorised or not) can filter an article using tags"""
        response = self.create_articles()
        response = self.client.get(reverse("articles:search-filter"), data={"tag": 'bev'})
        self.assertIn(b"never", response.content)

    def test_user_cant_filter_article_using_wrong_tag(self):
        """users cannot filter article using wrong or unavailable tags"""
        response = self.create_articles()
        response = self.client.get(reverse("articles:search-filter"), data={"tag": 'jkl'})
        data = json.loads(response.content)
        self.assertEqual(data['data']['article']['results'], [])

    def test_user_can_filter_article_using_author(self):
        """any user can filter an article using the author's username"""
        response = self.create_articles()
        response = self.client.get(reverse("articles:search-filter"), data={"username": 'beverly'})
        self.assertIn(b"love", response.content)

    def test_user_cant_filter_article_using_wrong_author(self):
        """user cannot filter articles using a wrong authors username"""
        response = self.create_articles()
        response = self.client.get(reverse("articles:search-filter"), data={"username": 'moses'})
        data = json.loads(response.content)
        self.assertEqual(data['data']['article']['results'], [])

    def test_user_can_filter_article_using_title(self):
        """user an filter existing artiles using their titles"""
        response = self.create_articles()
        response = self.client.get(reverse("articles:search-filter"), data={"title": 'greatest'})
        self.assertIn(b"bev", response.content)

    def test_user_cant_filter_article_using_wrong_title(self):
        """user cannot filter artiles using wrong titles"""
        response = self.create_articles()
        response = self.client.get(reverse("articles:search-filter"), data={"title": 'great'})
        data = json.loads(response.content)
        self.assertEqual(data['data']['article']['results'], [])

    def test_user_can_search_article_content(self):
        """user can searh the contents of all articles"""
        response = self.create_articles()
        response = self.client.get(reverse("articles:search-filter"), data={"search": 'more'})
        self.assertIn(b"never", response.content)
