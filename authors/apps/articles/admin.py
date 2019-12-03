from django.contrib import admin

# Register your models here.
from authors.apps.articles.models import Article, Tag, Comment, FavouriteArticle

admin.site.register(Article)
admin.site.register(Tag)

admin.site.register(Comment)
admin.site.register(FavouriteArticle)
