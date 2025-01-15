from django.contrib.auth import get_user_model, authenticate
from django.shortcuts import render
from djoser.views import UserViewSet, TokenCreateView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

from .models import Ingredient, Recipe, Tag
from .filters import RecipeFilter
from .permissions import IsAuthor
from .serializers import (
    IngredientSerializer, RecipeSerializer, RecipeSerializerForRead,
    UserModelSerializer, UserAvatarSerializer, SignupSerializer,
    TokenSerializer, ChangePasswordSerializer, TagSerializer
)

User = get_user_model()


class UserPagination(PageNumberPagination):
    page_size = 10  
    page_size_query_param = 'page_size'
    max_page_size = 100


class RecipePagination(PageNumberPagination):
    page_size = 6  
    page_size_query_param = 'page_size'
    max_page_size = 100


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
    
    @action(detail=False, methods=('get',), # убрала метод pach так как нет в требованиях. Код пока оставила
            permission_classes=(IsAuthenticated,))
    def me(self, request):
        """Эндпоинт для изменения профиля текущего пользователя."""
        if not request.user.is_authenticated:
            return Response({'detail': 'Пользователь не авторизован.'}, status=status.HTTP_401_UNAUTHORIZED)
        user = self.request.user
        # if request.method == 'GET':
        serializer =  UserModelSerializer(user)
        return Response(serializer.data)

        # serializer = self.get_serializer(user,
        #                                  data=request.data, partial=True)
        # serializer.is_valid(raise_exception=True)
        # serializer.save()
        # return Response(serializer.data)


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
    serializer_class = RecipeSerializer
    # pagination_class = PageNumberPagination
    # http_metod_names = ('get', 'post',)
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,
                       filters.OrderingFilter, filters.SearchFilter)
    filterset_class = RecipeFilter
    search_fields = ('name',)
    ordering_fields = ('name', 'tag')
    ordering = ('name',)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user,
                        ingredients=self.request.data['ingredients'])
    
    def get_permissions(self):
        """Выбор пермишена в зависимости от метода запроса."""
        if self.request.method in ['GET', 'POST']:
            return [AllowAny()]
        elif self.request.method == 'POST':
            return [IsAuthenticated()]
        return[IsAuthor()]
    
    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от метода запроса."""
        if self.request.method == 'GET':
            return RecipeSerializerForRead
        return RecipeSerializer
    
    def list(self, request):
        limit = request.query_params.get('limit',10)
        paginator = RecipePagination()
        queryset = self.queryset[:int(limit)]
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        serializer = RecipeSerializerForRead(paginated_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)


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
