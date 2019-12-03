from django.contrib.auth.models import AnonymousUser
from django.db.models import Count
from django.utils.text import slugify
from rest_framework import status, viewsets, generics
from rest_framework import mixins
from rest_framework.generics import DestroyAPIView, get_object_or_404, RetrieveAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.generics import (
    RetrieveUpdateDestroyAPIView, CreateAPIView, ListAPIView, ListCreateAPIView, UpdateAPIView,
)
from django.db import models
from collections import Counter
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as filters
from rest_framework.filters import SearchFilter, OrderingFilter

from authors.apps.articles.models import Article, Tag, ArticleRating, Comment, ArticleView, Violation, FavouriteArticle
from authors.apps.articles.serializers import (
    ArticleSerializer, TagSerializer, RatingSerializer, FavouriteSerializer, update, CommentSerializer,
    UpdateCommentSerializer, TagsSerializer, StatsSerializer, ViolationSerializer, ViolationListSerializer,
)
from authors.apps.authentication.models import User
from authors.apps.authentication.serializers import UserSerializer
from authors.apps.core.renderers import BaseJSONRenderer
from authors.apps.articles.permissions import IsArticleOwnerOrReadOnly, IsNotArticleOwner
from authors.apps.profiles.models import Profile
from authors.apps.profiles.serializers import ProfileSerializer
from .pagination import StandardResultsSetPagination
from notifications.signals import notify
from authors.apps.ah_notifications.notifications import Verbs
from authors.apps.core.mail_sender import send_email
from rest_framework.exceptions import NotFound


class ArticleAPIView(mixins.CreateModelMixin, mixins.UpdateModelMixin,
                     mixins.DestroyModelMixin, mixins.ListModelMixin,
                     mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Define the method to manipulate an article
    """
    lookup_field = 'slug'
    permission_classes = (
        IsAuthenticatedOrReadOnly,
        IsArticleOwnerOrReadOnly,
    )
    renderer_classes = (BaseJSONRenderer,)
    queryset = Article.objects.all()
    renderer_names = ('article', 'articles')
    serializer_class = ArticleSerializer
    pagination_class = StandardResultsSetPagination

    @staticmethod
    def retrieve_owner_or_published(slug, user):
        """
        Retrieve the article for a user,
        If the user is logged in:
            1. if the user is the owner, return the article whether it is published or not
            2. If the user is not the owner, return the article only if it is published
        If the user is not logged in:
            1. Return the article only if it is published
        :param slug:
        :param user:
        :return:
        """
        article = Article.objects.filter(slug=slug)
        if user and not isinstance(user, AnonymousUser):
            mine = Article.objects.filter(slug=slug, author=user)
            article = article.filter(published=True)

            article = article.union(mine).first()
        else:
            # ensure the article is published
            article = article.filter(published=True).first()
        return article

    def create(self, request, *args, **kwargs):
        """
        Creates an article.
        Set the author as the current logged in user
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        article = request.data.get('article', {})

        # prevent an unauthorized user to create an account
        if not request.user.is_verified:
            return Response({
                "errors":
                    "Sorry, verify your account first in order to create articles"
            }, status.HTTP_401_UNAUTHORIZED)

        serializer = self.serializer_class(data=article)
        serializer.is_valid(raise_exception=True)
        serializer.save(author=request.user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """
        Check whether the article exists and returns a custom message,

        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        slug = kwargs['slug']

        article = Article.objects.filter(slug=slug).first()
        if article is None:
            return Response({
                'errors': 'Article does not exist'
            }, status.HTTP_404_NOT_FOUND)
        elif not article.author == request.user:
            return Response(
                {
                    "errors": "You are not allowed to modify this article"
                }, status.HTTP_403_FORBIDDEN)

        serializer = self.serializer_class(
            article, data=request.data.get('article', {}), partial=True)
        serializer.is_valid(raise_exception=True)

        serializer.save(author=request.user)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve an article using the article slug
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        slug = kwargs['slug']

        article = self.retrieve_owner_or_published(slug, request.user)

        if article is None:
            return Response({
                'errors': 'Article does not exist'
            }, status.HTTP_404_NOT_FOUND)
        if request.user and not isinstance(request.user, AnonymousUser) and article.author != request.user:
            ArticleView.objects.get_or_create(article=article, user=request.user)
        serializer = self.serializer_class(
            article, context={'request': request})

        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        """
        Only list the articles that have been published
        :param request:
        :param args:
        :param kwargs:
        :return:
        """

        articles = Article.objects.filter(published=True)

        # if the user is logged in, display both published and unpublished articles
        if request.user and not isinstance(request.user, AnonymousUser):
            mine = Article.objects.filter(author=request.user)

            articles = articles.union(mine)

        # paginates a queryset(articles) if required
        page = self.paginate_queryset(articles)

        serializer = self.serializer_class(
            page,
            context={
                'request': request
            },
            many=True
        )
        return self.get_paginated_response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Return a custom message when the article has been deleted
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        super().destroy(self, request, *args, **kwargs)

        return Response({'message': 'The article has been deleted.'})


class ArticleFilter(filters.FilterSet):
    tag = filters.CharFilter(field_name='tags__tag', lookup_expr='exact')
    username = filters.CharFilter(field_name='author__username', lookup_expr='exact')
    title = filters.CharFilter(field_name='title', lookup_expr='exact')

    class Meta:
        model = Article
        fields = ['tag', 'username', 'title']


class ArticleTagsAPIView(generics.ListCreateAPIView, generics.DestroyAPIView):
    lookup_field = 'slug'
    serializer_class = TagSerializer
    renderer_classes = (BaseJSONRenderer,)
    queryset = Tag.objects.all()
    permission_classes = [IsArticleOwnerOrReadOnly, IsAuthenticatedOrReadOnly]

    def create(self, request, *args, **kwargs):  # NOQA : E731
        """
        Create a tag, and use it for a particular article,
        This method ensures there is no duplication of articles
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        slug = kwargs['slug']

        article = Article.objects.filter(
            slug=slug, author=request.user).first()
        if article is None:
            return Response({
                'errors': 'Article does not exist'
            }, status.HTTP_404_NOT_FOUND)

        else:
            tags = request.data.get('tags', [])
            serializer = self.serializer_class(
                many=True, data=[{
                    'tag': x
                } for x in tags])
            valid = serializer.is_valid(raise_exception=False)
            if not valid:
                errors = {}
                for i in range(0, len(serializer.errors)):
                    if len(serializer.errors[i]) > 0:
                        errors[tags[i]] = serializer.errors[i]
                return Response(errors, status.HTTP_400_BAD_REQUEST)

            for tag in tags:
                t, created = Tag.objects.get_or_create(
                    slug=slugify(tag), tag=tag)
                article.tags.add(t)

            output = TagsSerializer(article)

            return Response(output.data)

    def destroy(self, request, *args, **kwargs):
        slug = kwargs['slug']

        article = Article.objects.filter(
            slug=slug, author=request.user).first()
        if article is None:
            return Response({
                'errors': 'Article does not exist'
            }, status.HTTP_404_NOT_FOUND)
        else:
            tags = request.data.get('tags', [])

            # delete the tags from the article
            for tag in tags:
                t = Tag.objects.get(slug=slugify(tag))
                if t:
                    article.tags.remove(t)

            output = TagsSerializer(article)
            return Response(output.data)

    def list(self, request, *args, **kwargs):
        """
        Get all the tags for a particular article
        :param request:
        :param args:
        :param kwargs:
        :return:
        """

        slug = kwargs['slug']

        article = ArticleAPIView.retrieve_owner_or_published(
            slug, request.user)

        if article is None:
            return Response({
                'errors': 'Article does not exist'
            }, status.HTTP_404_NOT_FOUND)
        else:
            output = TagsSerializer(article)
            return Response(output.data)


class TagsAPIView(generics.ListAPIView):
    """
    API View class to display all the tags
    """
    queryset = Tag.objects.all()
    renderer_classes = (BaseJSONRenderer,)
    renderer_names = ('tag', 'tags')
    serializer_class = TagSerializer


class ReactionMixin(CreateAPIView, DestroyAPIView):
    permission_classes = (IsAuthenticated,)


class BaseReactionsMixin:
    """
    This mixin contains properties common to all reaction
    views.
    """

    def get_queryset(self):
        return Article.objects.all()

    def get_object(self):
        obj = get_object_or_404(self.get_queryset(), slug=self.kwargs["slug"])
        self.check_object_permissions(self.request, obj)
        return obj

    def get_reactions(self):
        article = self.get_object()
        serializer = ArticleSerializer(
            article, context={'request': self.request})
        return serializer.data['reactions']


class ReactionsAPIView(BaseReactionsMixin, RetrieveAPIView):
    """
    This view retrieves the reactions of an article.
    """

    def get(self, request, **kwargs):
        return Response({'reactions': self.get_reactions()})


class LikeDislikeMixin(BaseReactionsMixin, CreateAPIView, DestroyAPIView):
    """
    This mixin adds create and destroy API views and permission classes to the
    BaseReactionMixin. These properties are required required by the like
    and dislike views.
    """

    def get_response(self, message):
        return {
            'message': message,
            'reactions': self.get_reactions()
        }


class ArticleFilter(filters.FilterSet):
    tag = filters.CharFilter(field_name='tags__tag', lookup_expr='exact')
    username = filters.CharFilter(field_name='author__username', lookup_expr='exact')
    title = filters.CharFilter(field_name='title', lookup_expr='exact')

    class Meta:
        model = Article
        fields = ['tag', 'username', 'title']


class SearchFilterListAPIView(ListAPIView):
    serializer_class = ArticleSerializer
    permission_classes = (AllowAny,)
    renderer_classes = (BaseJSONRenderer,)
    renderer_names = ("article", "articles",)
    queryset = Article.objects.all()
    pagination_class = StandardResultsSetPagination

    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    # filter fields are used to filter the articles using the tags, author's username and title
    filterset_class = ArticleFilter
    # search fields search all articles' parameters for the searched character
    search_fields = ('tags__tag', 'author__username', 'title', 'body', 'description')
    # ordering fields are used to render search outputs in a particular order e.g asending or descending order
    ordering_fields = ('author__username', 'title')


class LikeAPIView(LikeDislikeMixin):
    """
    This view enables liking and un-liking articles.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request, **kwargs):
        """
        Like an article.
        """
        article = self.get_object()
        article.like(request.user)

        return Response(
            self.get_response('You like this article.'),
            status=status.HTTP_201_CREATED)

    def delete(self, request, **kwargs):
        """
        Un-like an article.
        """
        article = self.get_object()
        article.un_like(request.user)

        return Response(
            self.get_response('You no longer like this article.'),
            status=status.HTTP_200_OK)


class DislikeAPIView(LikeDislikeMixin):
    """
    This view enables disliking and un-disliking articles.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request, **kwargs):
        """
        Dislike an article.
        """
        article = self.get_object()
        article.dislike(request.user)

        return Response(
            self.get_response('You dislike this article.'),
            status=status.HTTP_201_CREATED)

    def delete(self, request, **kwargs):
        """
        Un-dislike an article.
        """
        article = self.get_object()
        article.un_dislike(request.user)

        return Response(
            self.get_response('You no longer dislike this article.'),
            status=status.HTTP_200_OK)


class RatingAPIView(CreateAPIView, RetrieveUpdateDestroyAPIView):
    permission_classes = (IsAuthenticated,)
    queryset = ArticleRating.objects.all()
    serializer_class = RatingSerializer
    renderer_classes = (BaseJSONRenderer,)
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'
    lookup_field = 'article__slug'

    def retrieve(self, request, *args, **kwargs):
        try:
            article = Article.objects.get(slug=kwargs['slug'])
        except Article.DoesNotExist:
            data = {"errors": "This article does not exist!"}
            return Response(data, status=status.HTTP_404_NOT_FOUND)

        user = request.user.id
        user_rating = ArticleRating.objects.filter(article=article, rated_by=user).first()

        serializer = self.get_serializer(user_rating)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):  # NOQA
        """
        Users can post article ratings
        """
        serializer_data = request.data.get('rating', {})

        try:
            article = Article.objects.get(slug=kwargs['slug'])
        except Article.DoesNotExist:
            data = {"errors": "This article does not exist!"}
            return Response(data, status=status.HTTP_404_NOT_FOUND)
        if article:
            rating = ArticleRating.objects.filter(article=article, rated_by=request.user).first()
            rating_author = article.author
            rating_user = request.user
            if rating_author == rating_user:
                data = {"errors": "You cannot rate your own article."}
                return Response(data, status=status.HTTP_403_FORBIDDEN)

            else:
                serializer = self.serializer_class(rating, data=serializer_data, partial=True)
                serializer.is_valid(raise_exception=True)

                notify.send(rating_user, verb=Verbs.ARTICLE_RATING, recipient=rating_author,
                            description="{} has rated your article {}/5".format(rating_user, rating))

                serializer.save(rated_by=request.user, article=article)

                data = serializer.data
                data['Message'] = "You have successfully rated this article"
                return Response(data, status=status.HTTP_201_CREATED)


class RatingsAPIView(RetrieveAPIView):
    queryset = ArticleRating.objects.all()
    serializer_class = RatingSerializer
    renderer_classes = (BaseJSONRenderer,)
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'
    lookup_field = 'article__slug'

    def retrieve(self, request, *args, **kwargs):
        try:
            article = Article.objects.get(slug=kwargs['slug'])
        except Article.DoesNotExist:
            data = {"errors": "This article does not exist!"}
            return Response(data, status=status.HTTP_404_NOT_FOUND)

        avg_rating = ArticleRating.objects.filter(article=article).aggregate(
            average_rating=models.Avg('rating'))['average_rating'] or 0
        total_user_rated = ArticleRating.objects.filter(
            article=article).count()

        each_rating = Counter(
            ArticleRating.objects.filter(article=article).values_list(
                'rating', flat=True))

        return Response({
            'avg_rating': avg_rating,
            'total_user': total_user_rated,
            'each_rating': each_rating
        }, status=status.HTTP_200_OK)


class CommentUsersAPIView(ListAPIView):
    serializer_class = ProfileSerializer
    permission_classes = (IsArticleOwnerOrReadOnly,)
    renderer_classes = (BaseJSONRenderer,)
    renderer_names = ('user', 'users')

    lookup_url_kwarg = 'slug'
    lookup_field = 'article__slug'

    def get_queryset(self):
        current = self.request.user.username
        """This method filter and get comment of an article."""
        comments = Comment.objects.filter(article__slug=self.kwargs['slug']) \
            .order_by('author__user_id').distinct('author__user_id')
        return [comment.author for comment in comments if comment.author != current]


class CommentAPIView(ListCreateAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    renderer_classes = (BaseJSONRenderer,)
    pagination_class = StandardResultsSetPagination
    renderer_names = ('comment', 'comments')
    """This class get commit for specific article and create comment"""

    # filter by slug from url
    lookup_url_kwarg = 'slug'
    lookup_field = 'article__slug'

    def filter_queryset(self, queryset):
        """This method filter and get comment of an article."""
        filters = {self.lookup_field: self.kwargs[self.lookup_url_kwarg], 'parent': None}
        return queryset.filter(**filters)

    def create(self, request, *args, **kwargs):
        """This methods creates a comment"""
        slug = self.kwargs['slug']
        try:
            article = Article.objects.get(slug=slug)
        except Article.DoesNotExist:
            return Response({
                'Error': 'Article does not exist'
            }, status.HTTP_404_NOT_FOUND)
        serializer = self.serializer_class(
            data=request.data.get('comment', {}))
        serializer.is_valid(raise_exception=True)

        serializer.save(article=article, author=request.user.profile)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CommentCreateUpdateDestroy(CreateAPIView, RetrieveUpdateDestroyAPIView):
    """This class view creates update and delete comment"""
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    renderer_classes = (BaseJSONRenderer,)
    renderer_names = ['comment', 'comments']
    pagination_class = StandardResultsSetPagination
    lookup_url_kwarg = "pk"

    def retrieve(self, request, *args, **kwargs):
        slug = self.kwargs['slug']

        try:
            article = Article.objects.get(slug=slug)
        except Article.DoesNotExist:
            return Response({
                'error': 'Article does not exist'
            }, status.HTTP_404_NOT_FOUND)

        # Get the parent comment of the thread
        try:
            pk = self.kwargs.get('pk')
            parent = Comment.objects.get(pk=pk)
        except Comment.DoesNotExist:
            message = {"error": "comment with this ID doesn't exist"}
            return Response(message, status.HTTP_404_NOT_FOUND)

        page = self.paginate_queryset(parent.thread.order_by('created_at').all())

        serializer = self.serializer_class(
            page,
            context={
                'request': request
            },
            many=True
        )
        response = self.get_paginated_response(serializer.data)
        response.data['comment'] = self.serializer_class(instance=parent, context={
            'request': request
        }).data
        return response

    def create(self, request, slug=None, pk=None):
        """This method creates child comment(thread-replies on the parent comment)"""
        slug = self.kwargs['slug']

        try:
            article = Article.objects.get(slug=slug)
        except Article.DoesNotExist:
            return Response({
                'error': 'Article does not exist'
            }, status.HTTP_404_NOT_FOUND)

        # Get the parent commet of the thread
        try:
            pk = self.kwargs.get('pk')
            parent = Comment.objects.get(pk=pk)
        except Comment.DoesNotExist:
            message = {"error": "comment with this ID doesn't exist"}
            return Response(message, status.HTTP_404_NOT_FOUND)

        # validating, deserializing and  serializing comment-thread.
        serializer = self.serializer_class(
            data=request.data.get('comment', {}))

        # send notifications to users mentioned in the comments
        mentions = request.data.get('mentions', [])

        for mention in mentions:
            notify.send(request.user, verb=Verbs.COMMENT_MENTION,
                        recipient=User.objects.get(username=mention),
                        target=article,
                        description="{} mentioned you in a comment".format(request.user.username))

        serializer.is_valid(raise_exception=True)
        serializer.save(
            article=article, parent=parent, author=request.user.profile)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """This method delele comment"""
        slug = self.kwargs['slug']

        try:
            Article.objects.get(slug=slug)
        except Article.DoesNotExist:
            return Response({
                'error': 'Article does not exist'
            }, status.HTTP_404_NOT_FOUND)
        try:
            pk = self.kwargs.get('pk')
            Comment.objects.get(pk=pk)
        except Comment.DoesNotExist:
            message = {"error": "comment with this ID doesn't exist"}
            return Response(message, status.HTTP_404_NOT_FOUND)

        super().destroy(self, request, *args, **kwargs)
        return Response({'message': 'The comment has been deleted.'})

    def update(self, request, *args, **kwargs):
        """This method update comment"""
        serializer_class = UpdateCommentSerializer
        slug = self.kwargs['slug']

        try:
            Article.objects.get(slug=slug)
        except Article.DoesNotExist:
            return Response({
                'error': 'Article does not exist'
            }, status.HTTP_404_NOT_FOUND)
        try:
            pk = self.kwargs.get('pk')
            comment = Comment.objects.get(pk=pk)
        except Comment.DoesNotExist:
            message = {"error": "comment with this ID doesn't exist"}
            return Response(message, status.HTTP_404_NOT_FOUND)

        updated_comment = serializer_class.update(
            data=request.data.get('comment', {}), instance=comment)
        return Response(
            self.serializer_class(updated_comment).data,
            status=status.HTTP_201_CREATED)


class FavouritesAPIView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    renderer_classes = (BaseJSONRenderer,)
    serializer_class = ArticleSerializer
    pagination_class = StandardResultsSetPagination
    renderer_names = ['article', 'articles']

    def get_queryset(self):
        articles = []
        results = FavouriteArticle.objects.filter(user=self.request.user).select_related('article')
        for result in results:
            articles.append(result.article)
        return articles


class FavouriteArticleApiView(APIView):
    """
    define method to favourite article
    """

    permission_classes = (IsAuthenticated,)
    queryset = FavouriteArticle.objects.all()

    def post(self, request, slug):
        """
        a registered user can favourite an article
        """
        try:
            article = Article.objects.get(slug=slug)
        except Article.DoesNotExist:
            raise NotFound("article does not exist")

        if article.author != request.user:
            FavouriteArticle.objects.get_or_create(article=article, user=request.user)
            return Response({
                'slug': article.slug,
                'favourited': True
            })
        else:
            return Response({"message": "You cannot favourite your own article"}, status.HTTP_400_BAD_REQUEST)

    def delete(self, request, slug):
        """
        a registered user can favourite an article
        """
        try:
            article = Article.objects.get(slug=slug)
        except Article.DoesNotExist:
            raise NotFound("article does not exist")

        if article.author != request.user:
            favourited = FavouriteArticle.objects.filter(article=article, user=request.user)
            favourited.delete()
            return Response({
                'slug': article.slug,
                'favourited': False
            })
        else:
            return Response({"message": "You cannot unfavourite your own article"}, status.HTTP_400_BAD_REQUEST)


class LikeComments(UpdateAPIView):
    """This class Handles likes of comment"""
    serializer_class = CommentSerializer

    def update(self, request, *args, **kwargs):  # NOQA
        """This method updates liking of comment"""
        slug = self.kwargs['slug']

        try:
            Article.objects.get(slug=slug)
        except Article.DoesNotExist:
            return Response({
                'Error': 'Article doesnot exist'
            }, status.HTTP_404_NOT_FOUND)
        try:
            pk = self.kwargs.get('pk')
            comment = Comment.objects.get(pk=pk)
        except Comment.DoesNotExist:
            message = {"Error": "comment with this ID doesn't exist"}
            return Response(message, status.HTTP_404_NOT_FOUND)

        # get the user
        user = request.user
        comment.dislikes.remove(user.id)

        # confirm if user has already liked comment and remove him if
        # clicks it again
        confirm = bool(user in comment.likes.all())
        if confirm is True:
            comment.likes.remove(user.id)
            return Response({'Success, You no longer like this comment'},
                            status.HTTP_200_OK)

        # notify the author
        notify.send(request.user, recipient=comment.author.user, verb=Verbs.COMMENT_LIKE,
                    description="{} liked your comment".format(request.user.username))

        # This add the user to likes lists
        comment.likes.add(user.id)
        message = {"Success": "You liked this comment"}
        return Response(message, status.HTTP_200_OK)


class DislikeComments(UpdateAPIView):
    """This class Handles dislikes of comment"""
    serializer_class = CommentSerializer

    def update(self, request, *args, **kwargs):  # NOQA
        """This method updates liking of comment"""
        slug = self.kwargs['slug']

        try:
            Article.objects.get(slug=slug)
        except Article.DoesNotExist:
            return Response({
                'Error': 'Article doesnot exist'
            }, status.HTTP_404_NOT_FOUND)
        try:
            pk = self.kwargs.get('pk')
            comment = Comment.objects.get(pk=pk)
        except Comment.DoesNotExist:
            message = {"Error": "comment with this ID doesn't exist"}
            return Response(message, status.HTTP_404_NOT_FOUND)
        # get the user
        user = request.user
        comment.likes.remove(user.id)

        # confirm if user has already disliked comment and remove him if
        # clicks it again
        confirm = bool(user in comment.dislikes.all())
        if confirm is True:
            comment.dislikes.remove(user.id)
            message = {"Success": "You undislike this comment"}
            return Response(message, status.HTTP_200_OK)

        # This add the user to dislikes lists
        comment.dislikes.add(user.id)
        message = {"success": "You disliked this comment"}
        return Response(message, status.HTTP_200_OK)


class ArticleStatsView(ListAPIView):
    """"""
    permission_classes = (IsAuthenticated,)
    serializer_class = StatsSerializer
    renderer_classes = (BaseJSONRenderer,)
    renderer_names = ('stat', 'stats')

    def get_queryset(self):
        return Article.objects.filter(author=self.request.user)


class ViolationTypesAPIView(APIView):
    renderer_classes = (BaseJSONRenderer,)
    render_names = ('type', 'types',)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        violations = Violation.represent_violation_types()
        return Response(violations)


class ReportViolationsAPIView(APIView):
    serializer_class = ViolationSerializer
    renderer_classes = (BaseJSONRenderer,)
    renderer_names = ('violation', 'violations')
    permission_classes = (IsAuthenticatedOrReadOnly, IsNotArticleOwner,)

    def post(self, request, slug):
        try:
            article = Article.objects.get(slug=slug, published=True)
        except Article.DoesNotExist:
            return Response({"errors": "The article does not exist."}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(self.request, article)

        data = request.data
        data['article'] = article
        data['reporter'] = request.user

        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        email_data = {
            'username': request.user.username,
            'article_slug': article.slug,
            'author': article.author.username,
            'report_category': serializer.data['type']
        }

        send_email(
            template='acknowledgement_email.html',
            data=email_data,
            to_email=request.user.email,
            subject='Report received',
        )

        message = 'Your report has been received. You will receive a confirmation email shortly.'

        return Response({'message': message}, status=status.HTTP_200_OK)


class ListViolationsAPIView(generics.ListAPIView):
    permission_classes = (IsAdminUser,)
    serializer_class = ViolationListSerializer
    renderer_classes = (BaseJSONRenderer,)
    render_names = ('violation', 'violations')

    def get_queryset(self):
        violations = Violation.objects.filter(status=Violation.pending).order_by('article__id').distinct('article__id')
        return violations


class ProcessViolationsAPIView(APIView):
    permission_classes = (IsAdminUser,)
    renderer_classes = (BaseJSONRenderer,)

    def get_error_response(self, message):
        return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, slug):
        decision = request.data.get('decision')

        if decision not in Violation.DECISION_TYPES.keys():
            return self.get_error_response("This violation decision '%s' is not valid." % decision)

        if not Article.objects.filter(slug=slug).exists():
            return Response({'error': 'The article does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        violations = Violation.objects.filter(article__slug=slug)
        # if the specified article has no violations we take no action
        if violations.count() < 1:
            return self.get_error_response('This article does not have any pending violation reports.')

        if decision == 'approve':
            # approve all violation reports
            decision_status = Violation.approved
            article = Article.objects.get(slug=slug)
            email_data = {'username': request.user.username, 'article': article.title}
            to_email = article.author.email
            template = 'confirmation_email.html'
            # send email to email owner
            send_email(data=email_data, template=template, subject='Violation attention', to_email=to_email)
            # soft-delete the article
            article.delete()

        elif decision == 'reject':
            # reject all violation reports
            decision_status = Violation.rejected
        for violation in violations:
            # update violation status accordingly
            violation.status = decision_status
            violation.save()
        return Response({'message': 'You have %s this violation.' % decision_status}, status=status.HTTP_200_OK)
