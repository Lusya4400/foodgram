from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.http import HttpResponse
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from djoser.views import UserViewSet
from rest_framework.authtoken.models import Token
from django_filters.rest_framework import DjangoFilterBackend

from .conctans import PAGE_SIZE_USERS, PAGE_SIZE_RESIPES, MAX_PAGE_SIZE
from .filters import RecipeFilter
from .models import (
    Ingredient, Recipe, Tag, Follow, Favorite, ShoppingCart, IngredientRecipe)
from .permissions import IsAuthor
from .serializers import (
    IngredientSerializer, RecipeSerializer, RecipeSerializerForRead,
    UserModelSerializer, UserAvatarSerializer, SignupSerializer,
    TokenSerializer, ChangePasswordSerializer, TagSerializer, FollowSerializer,
    FavoriteSerializer, ShoppingCartSerializer
)

User = get_user_model()


class UserPagination(PageNumberPagination):
    """Пагинатор для списка пользователей."""
    page_size = PAGE_SIZE_USERS
    page_size_query_param = 'limit'
    max_page_size = MAX_PAGE_SIZE

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


class RecipePagination(UserPagination):
    """Пагинатор для списка рецептов."""
    page_size = PAGE_SIZE_RESIPES


class UserModelViewSet(UserViewSet):
    """Вьюсет для управления пользователями."""
    queryset = User.objects.all()
    serializer_class = UserModelSerializer

    def get_permissions(self):
        """Выбор пермишена в зависимости от метода запроса."""
        if self.request.method in ['GET', 'POST']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def create(self, request):
        """Создание пользователя."""
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(
            serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=('post',),
            permission_classes=(IsAuthenticated,))
    def set_password(self, request):
        """Установка пароля."""
        if not request.user.is_authenticated:
            return Response(
                {'detail': 'Пользователь не авторизован.'},
                status=status.HTTP_401_UNAUTHORIZED)
        serializer = ChangePasswordSerializer(
            data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response(
                {"detail": "Пароль успешно изменен."},
                status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request):
        """Вывод списка пользователей с учетом огриничения limit."""
        limit = request.query_params.get('limit', 10)
        paginator = UserPagination()
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
        if not request.user.is_authenticated:
            return Response(
                {'detail': 'Пользователь не авторизован.'},
                status=status.HTTP_401_UNAUTHORIZED)
        user = self.request.user
        serializer = UserModelSerializer(user)
        return Response(serializer.data)


class TokenView(APIView):
    """Вьюсет управления токенами."""
    permission_classes = (AllowAny,)

    def post(self, request):
        """Получение токена."""
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.get(email=serializer.validated_data['email'])
        token, _ = Token.objects.get_or_create(user=user)

        return Response({'auth_token': token.key}, status=status.HTTP_200_OK)


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для управления рецептами."""
    queryset = Recipe.objects.all()
    http_method_names = ('get', 'post', 'patch', 'delete')
    serializer_class = RecipeSerializer
    filterset_class = RecipeFilter
    filter_backends = (DjangoFilterBackend,)
    pagination_class = RecipePagination

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
        serializer.save(author=self.request.user,
                        ingredients=self.request.data['ingredients'])


class IngredientViewSet(viewsets.ModelViewSet):
    """Вьюсет для управления ингредиентами."""
    queryset = Ingredient.objects.all()
    http_method_names = ('get')
    permission_classes = (AllowAny,)
    serializer_class = IngredientSerializer
    filter_backends = (filters.SearchFilter,)
    pagination_class = None
    search_fields = ('name',)

    def get_queryset(self):
        """Получение запроса."""
        queryset = super().get_queryset()
        name_query = self.request.query_params.get('name', None)
        if name_query:
            queryset = queryset.filter(name__istartswith=name_query)
        return queryset


class TagViewSet(viewsets.ModelViewSet):
    """Вьюсет для управления тегами."""
    queryset = Tag.objects.all()
    http_method_names = ('get')
    permission_classes = (AllowAny,)
    serializer_class = TagSerializer
    pagination_class = None


class RecipeLinkView(APIView):
    """Вьюсет для получения короткой ссылки."""
    def get(self, request, id):
        try:
            recipe = Recipe.objects.get(id=id)
            short_link = (
                f"{request.build_absolute_uri('/s/')[:-1]}/{recipe.code}/"
            )
            return Response(
                {'short-link': short_link}, status=status.HTTP_200_OK)
        except Recipe.DoesNotExist:
            return Response(
                {'error': 'Recipe not found'}, status=status.HTTP_404_NOT_FOUND
            )


class RecipeDetailView(APIView):
    """Вьюсет для перехода по короткой ссылке."""
    def get(self, request, code):
        try:
            recipe = Recipe.objects.get(code=code)
            return redirect(f'api/recipes/{recipe.id}/')
        except Recipe.DoesNotExist:
            return Response(
                {'error': 'Recipe not found'}, status=status.HTTP_404_NOT_FOUND
            )
        

class FollowViewSet(viewsets.ModelViewSet):
    """Вьюсет для управления подписками на пользователей."""
    queryset = None
    http_method_names = ('get', 'post', 'delete')
    permission_classes = (IsAuthenticated,)
    serializer_class = FollowSerializer
    pagination_class = UserPagination

    def get_queryset(self):
        """Получение запроса."""
        user = self.request.user
        return user.following_user.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """Создание полписки.

        В ответе выводится пользователь с ограниченным списком рецептов,
        в соответствие со значением параметра recipes_limit.
        """
        following_id = kwargs.get('id')
        try:
            following_user = User.objects.get(id=following_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "Пользователь не найден."},
                status=status.HTTP_404_NOT_FOUND)
        if Follow.objects.filter(
            user=request.user, following=following_user
        ).exists():
            return Response(
                {"detail": "Вы уже подписаны на этого пользователя."},
                status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data={'following': following_user.id})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        recipes_limit = request.query_params.get('recipes_limit', None)
        if recipes_limit:
            # Почему-то способ примененный в методе list тут не срабатывает.
            # Пришлось использовать более радикальный способ.
            for index in range(
                len(serializer.data["recipes"]) - 1, int(recipes_limit) - 1, -1
            ):
                del serializer.data['recipes'][index]
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request):
        """Получение списка подписок текущего пользователя.

        В список выводится пользователи, на которых подписан текущий.
        У каждого пользователя выводится список его рецептов  с ограничением,
        в соответствие со значением параметра recipes_limit"""
        user = request.user
        subscriptions = user.following_user.all()
        recipes_limit = request.query_params.get('recipes_limit', None)
        paginator = self.pagination_class()
        paginated_subscriptions = (
            paginator.paginate_queryset(subscriptions, request)
        )
        serializer = FollowSerializer(paginated_subscriptions, many=True)
        if recipes_limit:
            for index in range(len(serializer.data)):
                serializer.data[index]['recipes'] = (
                    serializer.data[index]['recipes'][:int(recipes_limit)]
                )
        return paginator.get_paginated_response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Удаление подписки на пользователя."""
        following_id = self.kwargs.get('id')
        try:
            User.objects.get(id=following_id)
        except User.DoesNotExist:
            return Response({"detail": "Пользователь не найден."},
                            status=status.HTTP_404_NOT_FOUND)
        follow_instance = Follow.objects.filter(
            user=request.user, following_id=following_id).first()
        if follow_instance:
            follow_instance.delete()
            return Response({"detail": "Подписка удалена."},
                            status=status.HTTP_204_NO_CONTENT)
        return Response({"detail": "Вы не подписаны на этого пользователя."},
                        status=status.HTTP_400_BAD_REQUEST)


class FavoriteViewSet(viewsets.ModelViewSet):
    """Вьюсет для управления списком избранных рецептов."""
    queryset = None
    http_method_names = ('post', 'delete')
    permission_classes = (IsAuthenticated,)
    serializer_class = FavoriteSerializer
    pagination_class = RecipePagination
    filterset_class = RecipeFilter

    def get_queryset(self):
        """Получение запроса."""
        user = self.request.user
        return user.favorite_user.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """Добавление рецепта в избранное."""
        recipe_id = kwargs.get('id')
        try:
            recipe_favorite_user = Recipe.objects.get(id=recipe_id)
        except Recipe.DoesNotExist:
            return Response({"detail": "Рецепт не найден."},
                            status=status.HTTP_404_NOT_FOUND)
        if Favorite.objects.filter(user=request.user,
                                   recipe=recipe_favorite_user).exists():
            return Response(
                {"detail": "Этот рецепт уже добавлен в избранное."},
                status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(
            data={'recipe': recipe_favorite_user.id})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """Удаление рецепта из избранного."""
        recipe_id = self.kwargs.get('id')
        try:
            Recipe.objects.get(id=recipe_id)
        except Recipe.DoesNotExist:
            return Response(
                {"detail": "Рецепт не найден."},
                status=status.HTTP_404_NOT_FOUND)
        recipe_favorite_instance = Favorite.objects.filter(
            user=request.user, recipe_id=recipe_id).first()
        if recipe_favorite_instance:
            recipe_favorite_instance.delete()
            return Response(
                {"detail": "Рецепт удален из избранного."},
                status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(
                {"detail": "Рецепт отсутствует в избранном."},
                status=status.HTTP_400_BAD_REQUEST)

    def get_permissions(self):
        """Выбор пермишена в зависимости от метода запроса."""
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return [IsAuthor()]


class ShoppingCartViewSet(viewsets.ModelViewSet):
    """Вьюсет для управления списком покупок."""
    queryset = None
    http_method_names = ('get', 'post', 'delete')
    serializer_class = ShoppingCartSerializer
    pagination_class = RecipePagination
    filterset_class = RecipeFilter

    def get_queryset(self):
        """Получение запроса."""
        user = self.request.user
        return user.shopping_user.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """Добавление рецепта в список покупок."""
        recipe_id = kwargs.get('id')
        try:
            recipe_shopping_user = Recipe.objects.get(id=recipe_id)
        except Recipe.DoesNotExist:
            return Response(
                {"detail": "Рецепт не найден."},
                status=status.HTTP_404_NOT_FOUND)
        if ShoppingCart.objects.filter(
            user=request.user, recipe=recipe_shopping_user
        ).exists():
            return Response(
                {"detail": "Этот рецепт уже добавлен в список покупок."},
                status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(
            data={'recipe': recipe_shopping_user.id})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """Удаление рецепта из списка покупок."""
        recipe_id = self.kwargs.get('id')
        try:
            Recipe.objects.get(id=recipe_id)
        except Recipe.DoesNotExist:
            return Response({"detail": "Рецепт не найден."},
                            status=status.HTTP_404_NOT_FOUND)
        recipe_shopping_instance = ShoppingCart.objects.filter(
            user=request.user, recipe_id=recipe_id).first()
        if recipe_shopping_instance:
            recipe_shopping_instance.delete()
            return Response(
                {"detail": "Рецепт удален из списка покупок."},
                status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(
                {"detail": "Рецепт отсутствует в списке покупок."},
                status=status.HTTP_400_BAD_REQUEST)

    def get_permissions(self):
        """Выбор пермишена в зависимости от метода запроса."""
        if self.request.method == 'DELETE':
            return [IsAuthor()]
        return [IsAuthenticated()]

    def download_shopping_list(self, request):
        """Выгрузка списка покупок в файл txt."""
        user = request.user
        shopping_cart = ShoppingCart.objects.filter(user=user)

        # Создаём словарь для хранения ингредиентов и их суммарного количества
        ingredients_summary = {}

        # Проходим по всем записям в списке покупок
        for item in shopping_cart:
            recipe = item.recipe
            # Получаем ингредиенты для каждого рецепта
            ingredients = recipe.ingredients.all()
            for ingredient in ingredients:
                # Получаем количество ингредиента для данного рецепта
                ingredient_quantity = IngredientRecipe.objects.get(
                    ingredient=ingredient, recipe=recipe).amount
                # Суммируем количества ингредиентов
                if ingredient.name in ingredients_summary:
                    ingredients_summary[ingredient.name] += ingredient_quantity
                else:
                    ingredients_summary[ingredient.name] = ingredient_quantity

        response_text = ""
        for ingredient_name, total_amount in ingredients_summary.items():
            ingredient_measurement_unit = Ingredient.objects.get(
                name=ingredient_name).measurement_unit
            response_text += (
                f"{ingredient_name} ({ingredient_measurement_unit}) —"
                f"{total_amount} \n")

        response = HttpResponse(response_text, content_type='text/plain')
        response[
            'Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
        return response
