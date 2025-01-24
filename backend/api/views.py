import logging

from django.contrib.auth import get_user_model
from django.shortcuts import redirect, get_object_or_404
from django.http import HttpResponse
from django.db.models import Sum, Count
from django.urls import reverse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from djoser.views import UserViewSet
from django_filters.rest_framework import DjangoFilterBackend

from .filters import RecipeFilter, IngredientFilter
from recipes.models import (
    Ingredient, Recipe, Tag, Follow, Favorite, ShoppingCart)
from .permissions import IsAuthor
from .serializers import (
    IngredientSerializer, RecipeSerializer, RecipeSerializerForRead,
    UserModelSerializer, UserAvatarSerializer, TagSerializer, FollowSerializer,
    FavoriteSerializer, ShoppingCartSerializer
)
from api.pagination import Pagination

User = get_user_model()

logger=logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

class UserModelViewSet(UserViewSet):
    """Вьюсет для управления пользователями."""
    queryset = User.objects.all()
    serializer_class = UserModelSerializer
    pagination_class = Pagination

    def get_permissions(self):
        """Выбор пермишена в зависимости от метода запроса."""
        route_name = self.request.resolver_match.url_name
        if (
            self.request.method == 'GET' and route_name not in [
                'subscriptions', 'users-me'
            ] or (self.request.method == 'POST' and (
                self.request.path in ['/api/users/', '/api/auth/']))
        ):
            return (AllowAny(),)
        return (IsAuthenticated(),)

    def update_avatar(self, request):
        """Обновление аватара."""
        serializer = UserAvatarSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy_avatar(self, request):
        """Удаление аватара."""
        request.user.avatar.delete()
        request.user.save()
        return Response(status=204)

    @action(detail=True, methods=('post',),
            permission_classes=(IsAuthenticated,))
    def subscribe(self, request, id):
        """Создание подписки."""
        following_user = get_object_or_404(User, id=id)
        serializer = FollowSerializer(
            data={'following': following_user.id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=('get',),
            permission_classes=(IsAuthenticated,))
    def subscriptions(self, request):
        """Получение списка подписок текущего пользователя."""
        user = request.user
        subscriptions = user.following_user.all()
        subscriptions = self.paginate_queryset(subscriptions)
        serializer = FollowSerializer(
            subscriptions, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=('delete',),
            permission_classes=(IsAuthenticated,))
    def unsubscribe(self, request, id):
        """Удаление подписки на пользователя."""
        following_user = get_object_or_404(User, id=id)
        deleted_count, _ = Follow.objects.filter(
            user=request.user, following=following_user).delete()

        if not deleted_count:
            return Response(
                {"detail": "Вы не подписаны на этого пользователя."},
                status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Подписка удалена."},
                        status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для управления рецептами."""
    queryset = Recipe.objects.all()
    http_method_names = ('get', 'post', 'patch', 'delete')
    serializer_class = RecipeSerializer
    filterset_class = RecipeFilter
    filter_backends = (DjangoFilterBackend,)
    pagination_class = Pagination

    def get_permissions(self):
        """Выбор пермишена в зависимости от метода запроса."""
        if self.request.method == 'GET':
            return (AllowAny(),)
        elif self.request.method == 'POST':
            return (IsAuthenticated(),)
        return (IsAuthor(),)

    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от метода запроса."""
        if self.request.method == 'GET':
            return RecipeSerializerForRead
        return RecipeSerializer

    def perform_create(self, serializer):
        """Создание рецепта."""
        serializer.save(author=self.request.user)

    @action(detail=True, methods=('post',),
            permission_classes=(IsAuthenticated,))
    def favorite(self, request, id=None):
        """Добавление рецепта в избранное."""
        recipe = get_object_or_404(Recipe, id=id)
        serializer = FavoriteSerializer(
            context={'request': request}, data={'recipe': recipe.id})
        serializer.is_valid(raise_exception=True)
        serializer.save(user=self.request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=('delete',),
            permission_classes=(IsAuthenticated,))
    def unfavorite(self, request, id=None):
        """Удаление рецепта из избранного."""
        recipe = get_object_or_404(Recipe, id=id)
        deleted_count, _ = Favorite.objects.filter(
            user=request.user, recipe=recipe).delete()
        if not deleted_count:
            return Response({"detail": "Рецепт отсутствует в избранном."},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"detail": "Рецепт удален из избранного."},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=True, methods=('post',),
            permission_classes=(IsAuthenticated,))
    def add_to_cart(self, request, id):
        """Добавление рецепта в список покупок."""
        recipe = get_object_or_404(Recipe, id=id)
        serializer = ShoppingCartSerializer(
            context={'request': request}, data={'recipe': recipe.id}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(user=self.request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=('delete',), permission_classes=(IsAuthor,))
    def remove_from_cart(self, request, id):
        """Удаление рецепта из списка покупок."""
        recipe = get_object_or_404(Recipe, id=id)
        deleted_count, _ = ShoppingCart.objects.filter(
            user=request.user, recipe=recipe).delete()
        if not deleted_count:
            return Response(
                {"detail": "Рецепт отсутствует в списке покупок."},
                status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"detail": "Рецепт удален из списка покупок."},
            status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=('get',),
            permission_classes=(IsAuthenticated,))
    def download_shopping_list(self, request):
        """Выгрузка списка покупок в файл txt."""
        user = request.user
        ingredients_summary = (
            ShoppingCart.objects.filter(user=user)
            .values(
                'recipe__ingredients__name',
                'recipe__ingredients__measurement_unit' 
            )
            .annotate(total_amount=Sum(
                'recipe__ingredients__ingredientrecipe__amount', distinct=True
            ))
        )

        logger.debug(f'ingredients {ingredients_summary}')

        response_text = ""
        for ingredient in ingredients_summary:
            ingredient_name = ingredient['recipe__ingredients__name']
            meash_unit = ingredient['recipe__ingredients__measurement_unit']
            total_amount = ingredient['total_amount']
            response_text += (
                f"{ingredient_name} ({meash_unit})"
                f"— {total_amount} \n")

        response = HttpResponse(response_text, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="shoplist.txt"'
        return response


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для управления ингредиентами."""
    queryset = Ingredient.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    pagination_class = None
    search_fields = ('name',)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для управления тегами."""
    queryset = Tag.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = TagSerializer
    pagination_class = None


class RecipeLinkView(APIView):
    """Вьюсет для получения короткой ссылки."""
    def get(self, request, id):
        recipe = get_object_or_404(Recipe, id=id)
        short_link = (
            f"{request.build_absolute_uri('/s/')[:-1]}/"
            f"{recipe.short_code}/"
        )
        return Response(
            {'short-link': short_link}, status=status.HTTP_200_OK)


class RecipeDetailView(APIView):
    """Вьюсет для перехода по короткой ссылке."""
    def get(self, request, short_code):
        recipe = get_object_or_404(Recipe, short_code=short_code)
        recipe_detail_url = reverse('recipe-detail', kwargs={'pk': recipe.id})
        return redirect(recipe_detail_url)
