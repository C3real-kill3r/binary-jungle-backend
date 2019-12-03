from django.apps import AppConfig


class ArticlesAppConfig(AppConfig):
    name = 'authors.apps.articles'
    label = 'articles'
    verbose_name = 'Articles'

    def ready(self):
        import authors.apps.articles.signals

default_app_config = 'authors.apps.articles.ArticlesAppConfig'