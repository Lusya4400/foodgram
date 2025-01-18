import logging

from django.contrib.auth import get_user_model, authenticate
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from djoser.views import UserViewSet, TokenCreateView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status, viewsets, filters, mixins
from rest_framework.decorators import action
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

from .models import Ingredient, Recipe, Tag, Follow, Favorite, ShoppingCart, IngredientRecipe
from .filters import RecipeFilter
from .permissions import IsAuthor
from .serializers import (
    IngredientSerializer, RecipeSerializer, RecipeSerializerForRead,
    UserModelSerializer, UserAvatarSerializer, SignupSerializer,
    TokenSerializer, ChangePasswordSerializer, TagSerializer, FollowSerializer,
    FavoriteSerializer, ShoppingCartSerializer
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

User = get_user_model()
PAGE_SIZE_USERS = 6
PAGE_SIZE_RESIPES = 6

class UserPagination(PageNumberPagination):
    page_size = PAGE_SIZE_USERS
    page_size_query_param = 'limit'
    max_page_size = 100
    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


class RecipePagination(UserPagination):
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
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=('post',),
            permission_classes=(IsAuthenticated,))
    def set_password(self, request):
        if not request.user.is_authenticated:
            return Response({'detail': 'Пользователь не авторизован.'}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({"detail": "Пароль успешно изменен."}, status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request):
        limit = request.query_params.get('limit',10)
        paginator = UserPagination()
        queryset = self.queryset[:int(limit)]
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(paginated_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)

    def update_avatar(self, request):
        serializer = UserAvatarSerializer(request.user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
    
    def destroy_avatar(self, request):
        request.user.avatar = None
        request.user.save()
        return Response(status=204)
    
    @action(detail=False, methods=('get',), 
            permission_classes=(IsAuthenticated,))
    def me(self, request):
        """Эндпоинт для изменения профиля текущего пользователя."""
        if not request.user.is_authenticated:
            return Response({'detail': 'Пользователь не авторизован.'}, status=status.HTTP_401_UNAUTHORIZED)
        user = self.request.user
        serializer =  UserModelSerializer(user)
        return Response(serializer.data)


class TokenView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.get(email=serializer.validated_data['email'])
        token, _ = Token.objects.get_or_create(user=user)

        return Response({'auth_token': token.key}, status=status.HTTP_200_OK)


class RecipeViewSet(viewsets.ModelViewSet):
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
        return[IsAuthor()]
    
    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от метода запроса."""
        if self.request.method == 'GET':
            return RecipeSerializerForRead
        return RecipeSerializer
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user,
                        ingredients=self.request.data['ingredients'])

    # def list(self, request):
    #     queryset = self.filter_queryset(self.get_queryset())
    #    # limit = request.query_params.get('limit', 10)
    #     paginator = self.pagination_class()
    #   #  paginated_queryset = paginator.paginate_queryset(queryset[:int(limit)], request)
    #     paginated_queryset = paginator.paginate_queryset(queryset, request)
    #     serializer = RecipeSerializerForRead(paginated_queryset, many=True)
    #     return paginator.get_paginated_response(serializer.data)




class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    http_method_names = ('get')
    permission_classes = (AllowAny,)
    serializer_class = IngredientSerializer
    filter_backends = (filters.SearchFilter,)
    pagination_class = None
    search_fields = ('name',)

    def get_queryset(self):
        queryset = super().get_queryset()
        name_query = self.request.query_params.get('name', None)
        if name_query:
            queryset = queryset.filter(name__istartswith=name_query)  # Фильтрация по началу
        return queryset


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    http_method_names = ('get')
    permission_classes = (AllowAny,)
    serializer_class = TagSerializer
    pagination_class = None


class RecipeLinkView(APIView):
    def get(self, request, id):
        try:
            recipe = Recipe.objects.get(id=id)
            #short_link = f"{request.build_absolute_uri(reverse('recipe-detail', args=[recipe.code]))}"
            #short_link = f"{request.build_absolute_uri(reverse('recipe-link', args=[]))}{recipe.code}"
            short_link = f"{request.build_absolute_uri('/')[:-1]}/{recipe.code}/"
            return Response({'short-link': short_link}, status=status.HTTP_200_OK)
        except Recipe.DoesNotExist:
            return Response({'error': 'Recipe not found'}, status=status.HTTP_404_NOT_FOUND)


class FollowViewSet(viewsets.ModelViewSet): 
    queryset = None
    http_method_names = ('get', 'post', 'delete')    
    permission_classes = (IsAuthenticated,)
    serializer_class = FollowSerializer
    pagination_class = UserPagination
    # filter_backends = (filters.SearchFilter,) 
    # search_fields = ('following__username',) 

    def get_queryset(self): 
        user = self.request.user 
        return user.following_user.all() 

    def perform_create(self, serializer): 
        serializer.save(user=self.request.user)
    
    # def create(self, request, *args, **kwargs):
    #     following_id = kwargs.get('id')  # Получаем ID из URL
    #     try:
    #         following_user = User.objects.get(id=following_id)
    #     except User.DoesNotExist:
    #         return Response({"detail": "Рецепт не найден."}, status=status.HTTP_404_NOT_FOUND)    
    #     if Follow.objects.filter(user=request.user, following=following_user).exists():
    #         return Response({"detail": "Этот рецепт уже добавлен в избранное."}, status=status.HTTP_400_BAD_REQUEST)
    #     serializer = self.get_serializer(data={'recipe': following_user.id})
    #     serializer.is_valid(raise_exception=True)
    #     self.perform_create(serializer)
    #     return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def create(self, request, *args, **kwargs):
        print('открыто')
        following_id = kwargs.get('id')  # Получаем ID из URL
        try:
            following_user = User.objects.get(id=following_id)
        except User.DoesNotExist:
            return Response({"detail": "Пользователь не найден."}, status=status.HTTP_404_NOT_FOUND)    
        if Follow.objects.filter(user=request.user, following=following_user).exists():
            return Response({"detail": "Вы уже подписаны на этого пользователя."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data={'following': following_user.id})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        recipes_limit = request.query_params.get('recipes_limit', None)
        print(f'{recipes_limit}')
        if recipes_limit:
            logger.debug(f'Validated {serializer.data["recipes"]}')
            #for index in range(len(serializer.data)):
              #  serializer.data[index]['recipes'] = serializer.data[index]['recipes'][:int(recipes_limit)]
            for index in range (len(serializer.data["recipes"])-1, int(recipes_limit)-1, -1):
                print(f'индекс {index}')
                del serializer.data['recipes'][index]
           # serializer.data['recipes'] = (serializer.data['recipes'])[:int(recipes_limit)]
            logger.debug(f'Validated {len(serializer.data["recipes"])}')
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def list(self, request):
        """Получить список подписок текущего пользователя."""
        user = request.user
        subscriptions = user.following_user.all()
        recipes_limit = request.query_params.get('recipes_limit', None)
        paginator = self.pagination_class()
        paginated_subscriptions = paginator.paginate_queryset(subscriptions, request)
        serializer = FollowSerializer(paginated_subscriptions, many=True)
        if recipes_limit:
          #  print(f"Используется лимит: {recipes_limit}")
            for index in range(len(serializer.data)):
                serializer.data[index]['recipes'] = serializer.data[index]['recipes'][:int(recipes_limit)]
        return paginator.get_paginated_response(serializer.data)
    
        # user = request.user
        # subscriptions = user.following_user.all()
        # serializer = FollowSerializer(subscriptions, many=True)
        # return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Удалить подписку на пользователя."""
        following_id = self.kwargs.get('id')
        try:
            user = User.objects.get(id=following_id)
        except User.DoesNotExist:
            return Response({"detail": "Пользователь не найден."}, status=status.HTTP_404_NOT_FOUND)
        follow_instance = Follow.objects.filter(user=request.user, following_id=following_id).first()
        if follow_instance:
            follow_instance.delete()
            return Response({"detail": "Подписка удалена."}, status=status.HTTP_204_NO_CONTENT)
        return Response({"detail": "Вы не подписаны на этого пользователя."}, status=status.HTTP_400_BAD_REQUEST)
    
class FavoriteViewSet(viewsets.ModelViewSet): 
    queryset = None
    http_method_names = ('post', 'delete')    
    permission_classes = (IsAuthenticated,)
    serializer_class = FavoriteSerializer
    pagination_class = RecipePagination
    filterset_class = RecipeFilter

    def get_queryset(self): 
        user = self.request.user 
        return user.favorite_user.all()
    
    def perform_create(self, serializer): 
        serializer.save(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        recipe_id = kwargs.get('id')  # Получаем ID из URL
        try:
            recipe_favorite_user = Recipe.objects.get(id=recipe_id)
        except Recipe.DoesNotExist:
            return Response({"detail": "Рецепт не найден."}, status=status.HTTP_404_NOT_FOUND)    
        if Favorite.objects.filter(user=request.user, recipe=recipe_favorite_user).exists():
            return Response({"detail": "Этот рецепт уже добавлен в избранное."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data={'recipe': recipe_favorite_user.id})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        """Удалить рецепт из избранного."""
        recipe_id = self.kwargs.get('id')
        try:
            recipe = Recipe.objects.get(id=recipe_id)
        except Recipe.DoesNotExist:
            return Response({"detail": "Рецепт не найден."}, status=status.HTTP_404_NOT_FOUND)
        recipe_favorite_instance = Favorite.objects.filter(user=request.user, recipe_id=recipe_id).first()
        if recipe_favorite_instance:
            recipe_favorite_instance.delete()
            return Response({"detail": "Рецепт удален из избранного."}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"detail": "Рецепт отсутствует в избранном."}, status=status.HTTP_400_BAD_REQUEST)

    def get_permissions(self):
        """Выбор пермишена в зависимости от метода запроса."""
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return[IsAuthor()]
    
class ShoppingCartViewSet(viewsets.ModelViewSet): 
    queryset = None
    http_method_names = ('get', 'post', 'delete')    
    serializer_class = ShoppingCartSerializer
    pagination_class = RecipePagination
    filterset_class = RecipeFilter

    def get_queryset(self): 
        user = self.request.user 
        return user.shopping_user.all()
    
    def perform_create(self, serializer): 
        serializer.save(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        recipe_id = kwargs.get('id')  # Получаем ID из URL
        try:
            recipe_shopping_user = Recipe.objects.get(id=recipe_id)
        except Recipe.DoesNotExist:
            return Response({"detail": "Рецепт не найден."}, status=status.HTTP_404_NOT_FOUND)    
        if ShoppingCart.objects.filter(user=request.user, recipe=recipe_shopping_user).exists():
            return Response({"detail": "Этот рецепт уже добавлен в список покупок."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data={'recipe': recipe_shopping_user.id})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        """Удалить рецепт из списка покупок."""
        recipe_id = self.kwargs.get('id')
        try:
            Recipe.objects.get(id=recipe_id)
        except Recipe.DoesNotExist:
            return Response({"detail": "Рецепт не найден."}, status=status.HTTP_404_NOT_FOUND)
        recipe_shopping_instance = ShoppingCart.objects.filter(user=request.user, recipe_id=recipe_id).first()
        if recipe_shopping_instance:
            recipe_shopping_instance.delete()
            return Response({"detail": "Рецепт удален из списка покупок."}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"detail": "Рецепт отсутствует в списке покупок."}, status=status.HTTP_400_BAD_REQUEST)

    def get_permissions(self):
        """Выбор пермишена в зависимости от метода запроса."""
        if self.request.method == 'DELETE':
            return[IsAuthor()]
        return [IsAuthenticated()]
    
    def download_shopping_list(self, request):
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
                ingredient_quantity = IngredientRecipe.objects.get(ingredient=ingredient, recipe=recipe).amount               
                # Суммируем количества ингредиентов
                if ingredient.name in ingredients_summary:
                    ingredients_summary[ingredient.name] += ingredient_quantity
                else:
                    ingredients_summary[ingredient.name] = ingredient_quantity
                    
        response_text = ""
        for ingredient_name, total_amount in ingredients_summary.items():
            ingredient_measurement_unit = Ingredient.objects.get(name=ingredient_name).measurement_unit
            response_text += f"{ingredient_name} ({ingredient_measurement_unit}) — {total_amount} \n"

        response = HttpResponse(response_text, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
        return response
