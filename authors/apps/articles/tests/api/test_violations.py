import json

from rest_framework import status
from rest_framework.reverse import reverse
from authors.apps.articles.models import Article, Violation
from authors.apps.articles.tests.api.test_articles import BaseArticlesTestCase
from authors.apps.core.test_helpers import set_test_client, login, logout


class BaseViolationsTestCase(BaseArticlesTestCase):
    """
    This class tests reporting articles that violates rules of engagements
    """

    def setUp(self):
        super().setUp()
        set_test_client(self.client)
        logout()

    def report(self, article_slug, violation='inappropriate_content'):
        return self.client.post(
            reverse('articles:report-violations', kwargs={'slug': article_slug}),
            data={'type': violation, 'description': 'Foo Bar Baz'},
            format='json'
        )

    def generate_article(self, published=True, field='slug', return_obj=False):
        """
        Creates an article and returns the field specified by the field
        argument. If return_obj is set to True is returns the created
        article object instead of the specified field.
        :param published:
        :param field:
        :param return_obj:
        :return:
        """
        article = self.create_article(published=published)

        if return_obj:
            return Article.objects.get(slug=article['slug'])

        return article[field]


class GetViolationTypesTestCase(BaseViolationsTestCase):
    def setUp(self):
        super().setUp()
        logout()

    def violation_types(self):
        return self.client.get(reverse('articles:violation-types'), format='json')

    def test_user_can_see_violation_types(self):
        login()
        self.assertEqual(self.violation_types().data, Violation.represent_violation_types())

    def test_unauthenticated_user_cannot_see_violation_types(self):
        response = self.violation_types()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ReportViolationsTestCase(BaseViolationsTestCase):
    def setUp(self):
        super().setUp()
        logout()

    def test_users_can_report_articles(self):
        login(verified=True)
        slug = self.generate_article(published=True)
        login()
        response = self.report(slug)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(
            b"Your report has been received. You will receive a confirmation email shortly.",
            response.content
        )

    def test_users_cannot_report_their_own_articles(self):
        login(verified=True)
        slug = self.generate_article(published=True)
        response = self.report(slug)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn(b"You cannot perform this action on your own article", response.content)

    def test_unauthenticated_users_cannot_report_articles(self):
        login(verified=True)
        slug = self.generate_article(published=True)
        logout()
        response = self.report(slug)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_users_cannot_report_non_existent_articles(self):
        login(verified=True)
        response = self.report('foo-bar')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_users_cannot_report_an_article_more_than_once(self):
        login(verified=True)
        slug = self.generate_article(published=True)
        login()
        response = self.report(slug)  # report for the first time
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.report(slug)  # report for the second time
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(b"You cannot report an article more than once.", response.content)


class AdminViolationsTestCase(BaseViolationsTestCase):
    def setUp(self):
        super().setUp()
        login(verified=True)
        self.reported1 = self.generate_article(published=True)
        self.reported2 = self.generate_article(published=True)
        login()
        self.report(self.reported1)
        self.report(self.reported2)
        login()
        self.report(self.reported1)
        self.report(self.reported2)
        logout()


class ListViolationsTestCase(AdminViolationsTestCase):
    def setUp(self):
        super().setUp()
        logout()

    def reported_violations(self):
        return self.client.get(reverse('articles:violations'))

    def test_admin_can_view_violations(self):
        login(admin=True)
        response = self.reported_violations()
        data = json.dumps(response.data)
        self.assertIn(self.reported1, data)
        self.assertIn(self.reported2, data)

    def test_ordinary_user_cannot_view_violations(self):
        login()
        response = self.reported_violations()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ProcessViolationsTestCase(AdminViolationsTestCase):
    def setUp(self):
        super().setUp()
        logout()

    def process_violation(self, slug, decision):
        return self.client.put(
            reverse('articles:process-violations', kwargs={'slug': slug}),
            data={'decision': decision},
            format='json'
        )

    def test_admin_can_reject_article_violation_reports(self):
        login(admin=True)
        response = self.process_violation(self.reported1, 'reject')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("You have rejected this violation.", response.data['message'])

    def test_admin_can_approve_article_violation_reports(self):
        login(admin=True)
        response = self.process_violation(self.reported1, 'approve')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("You have approved this violation.", response.data['message'])

    def test_invalid_decisions_are_not_allowed(self):
        login(admin=True)
        response = self.process_violation(self.reported1, 'foobar')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("This violation decision 'foobar' is not valid.", response.data['error'])

    def test_article_without_violations_cannot_be_processed(self):
        login(verified=True)
        clean_article = self.generate_article(published=True)
        login(admin=True)
        response = self.process_violation(clean_article, 'approve')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("This article does not have any pending violation reports.", response.data['error'])

    def test_non_existent_article_cannot_be_processed(self):
        login(admin=True)
        response = self.process_violation('foobar', 'reject')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("The article does not exist.", response.data['error'])

    def test_ordinary_users_cannot_process_article_violation_reports(self):
        login()
        response = self.process_violation(self.reported1, 'reject')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.process_violation(self.reported1, 'approve')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
