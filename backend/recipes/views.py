from django.contrib.auth import get_user_model
from django.shortcuts import redirect, get_object_or_404
from django.http import HttpResponse
from django.db.models import Sum
from django.urls import reverse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from djoser.views import UserViewSet
from django_filters.rest_framework import DjangoFilterBackend

from api.filters import RecipeFilter, IngredientFilter
from .models import (
    Ingredient, Recipe, Tag, Follow, Favorite, ShoppingCart)
from api.permissions import IsAuthor
from api.serializers import (
    IngredientSerializer, RecipeSerializer, RecipeSerializerForRead,
    UserModelSerializer, UserAvatarSerializer, TagSerializer, FollowSerializer,
    FavoriteSerializer, ShoppingCartSerializer
)
from api.pagination import Pagination

User = get_user_model()


class UserModelViewSet(UserViewSet):
    """Вьюсет для управления пользователями."""
    queryset = User.objects.all()
    serializer_class = UserModelSerializer
    pagination_class = Pagination

    def get_permissions(self):
        """Выбор пермишена в зависимости от метода запроса."""
        if self.request.method in ['GET', 'POST']:
            return [AllowAny()]
        return [IsAuthenticated()]

    # Без этого метода в список пользователей выводится только текущий
    # пользователь, несмотря на то, что выполены настройки joser в settings
    # 'PERMISSIONS':{'user_list': ['rest_framework.permissions.AllowAny'],},
    def list(self, request):
        """Вывод списка пользователей с учетом огриничения limit."""
        limit = request.query_params.get('limit', 10)
        paginator = Pagination()
        queryset = self.queryset[:int(limit)]
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(paginated_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)

    def update_avatar(self, request):
        """Обновление аватара."""
        serializer = UserAvatarSerializer(request.user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def destroy_avatar(self, request):
        """Удаление аватара."""
        request.user.avatar = None
        request.user.save()
        return Response(status=204)

    @action(detail=False, methods=('get',),
            permission_classes=(IsAuthenticated,))
    def me(self, request):
        """Эндпоинт для изменения профиля текущего пользователя."""
        # если убрать проверку, то при запросе от анонимного пользователя
        # вылетает ошибка
        # Original exception text was:
        # 'AnonymousUser' object has no attribute 'email'.
        if not request.user.is_authenticated:
            return Response(
                {'detail': 'Пользователь не авторизован.'},
                status=status.HTTP_401_UNAUTHORIZED)
        return super().me(request)

    @action(detail=True, methods=['post'],
            permission_classes=(IsAuthenticated,))
    def subscribe(self, request, id):
        """Создание подписки."""
        if request.user.is_anonymous:
            return Response({"detail": "Необходима авторизация."},
                            status=status.HTTP_401_UNAUTHORIZED)
        following_user = get_object_or_404(User, id=id)
        serializer = FollowSerializer(
            data={'following': following_user.id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        """Получение списка подписок текущего пользователя."""
        user = request.user
        subscriptions = user.following_user.all()
        paginator = Pagination()
        subscriptions = paginator.paginate_queryset(subscriptions, request)
        serializer = FollowSerializer(
            subscriptions, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    @action(detail=True, methods=['delete'],
            permission_classes=[IsAuthenticated])
    def unsubscribe(self, request, id):
        """Удаление подписки на пользователя."""
        following_user = get_object_or_404(User, id=id)
        follow_instance = Follow.objects.filter(
            user=request.user, following=following_user).first()

        if follow_instance:
            follow_instance.delete()
            return Response({"detail": "Подписка удалена."},
                            status=status.HTTP_204_NO_CONTENT)

        return Response({"detail": "Вы не подписаны на этого пользователя."},
                        status=status.HTTP_400_BAD_REQUEST)


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
            return [AllowAny()]
        elif self.request.method == 'POST':
            return [IsAuthenticated()]
        return [IsAuthor()]

    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от метода запроса."""
        if self.request.method == 'GET':
            return RecipeSerializerForRead
        return RecipeSerializer

    def perform_create(self, serializer):
        """Создание рецепта."""
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, id=None):
        """Добавление рецепта в избранное."""
        recipe = get_object_or_404(Recipe, id=id)
        serializer = FavoriteSerializer(
            context={'request': request}, data={'recipe': recipe.id})
        serializer.is_valid(raise_exception=True)
        serializer.save(user=self.request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'],
            permission_classes=[IsAuthenticated])
    def unfavorite(self, request, id=None):
        """Удаление рецепта из избранного."""
        recipe = get_object_or_404(Recipe, id=id)
        favorite_instance = Favorite.objects.filter(
            user=request.user, recipe=recipe).first()
        if favorite_instance:
            favorite_instance.delete()
            return Response(
                {"detail": "Рецепт удален из избранного."},
                status=status.HTTP_204_NO_CONTENT
            )
        return Response({"detail": "Рецепт отсутствует в избранном."},
                        status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'],
            permission_classes=[IsAuthenticated])
    def add_to_cart(self, request, id):
        """Добавление рецепта в список покупок."""
        recipe = get_object_or_404(Recipe, id=id)
        serializer = ShoppingCartSerializer(
            context={'request': request}, data={'recipe': recipe.id}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(user=self.request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], permission_classes=[IsAuthor])
    def remove_from_cart(self, request, id):
        """Удаление рецепта из списка покупок."""
        recipe = get_object_or_404(Recipe, id=id)
        shopping_cart_instance = ShoppingCart.objects.filter(
            user=request.user, recipe=recipe).first()
        if shopping_cart_instance:
            shopping_cart_instance.delete()
            return Response(
                {"detail": "Рецепт удален из списка покупок."},
                status=status.HTTP_204_NO_CONTENT)
        return Response({"detail": "Рецепт отсутствует в списке покупок."},
                        status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
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
                'recipe__ingredients__ingredientrecipe__amount'
            ))
        )

        response_text = ""
        for ingredient in ingredients_summary:
            ingredient_name = ingredient['recipe__ingredients__name']
            meash_unit = ingredient['recipe__ingredients__measurement_unit']
            total_amount = ingredient['total_amount']
            response_text += (
                f"{ingredient_name} ({meash_unit})"
                f"— {total_amount}\n"
            )

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
