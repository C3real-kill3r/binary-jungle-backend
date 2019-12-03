from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    """
    A page number style that supports page numbers as
    query params
    `example usage`
    http://localhost:8000/api/articles/?page=3
    http://localhost:8000/api/articles?page=4&page_size=100
    """

    # the default page size
    page_size = 20

    # client can control the page using this query parameter
    page_size_query_param = 'page_size'

    # limits the max page size the client may request
    max_page_size = 10

    # overiding this method removes the posibility of pagination
    # yielding inconsistent results with unordered object_list
    def paginate_queryset(self, queryset, request, view=None):
        self.django_paginator_class._check_object_list_is_ordered = lambda s: None
        return super().paginate_queryset(queryset, request, view=view)

    def get_paginated_response(self, data):
        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'results': data
        })
