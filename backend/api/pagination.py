from rest_framework.pagination import PageNumberPagination

from recipes.constans import PAGE_SIZE_USERS


class Pagination(PageNumberPagination):
    """Пагинатор для списка пользователей."""
    page_size = PAGE_SIZE_USERS
    page_size_query_param = 'limit'
