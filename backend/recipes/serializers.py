import base64
import datetime as dt

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db.models import Q
from rest_framework import serializers

from .models import Ingredient, IngredientRecipe, Recipe, Tag
from .validators import validate_username
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.validators import UniqueTogetherValidator
from rest_framework_simplejwt.tokens import RefreshToken

MAX_LENGTH_150 = 150
MAX_LENGTH_254 = 254

User = get_user_model()


class SignupSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=MAX_LENGTH_254, required=True)
    username = serializers.CharField(
        max_length=MAX_LENGTH_150,
        required=True,
        validators=[validate_username],
    )
    first_name = serializers.CharField(max_length=MAX_LENGTH_150, required=True)
    last_name = serializers.CharField(max_length=MAX_LENGTH_150, required=True)
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name', 'password')
        
        validators = [
            UniqueTogetherValidator(
                queryset=User.objects.all(),
                fields=('username', 'email'),
                message='Пользователь с такими email и '
                'именем пользователя(ником) уже зарегистрирован в системе!'
            )
        ]
        
    def validate(self, data):
        """
        Проверяем пользователя в базе данных.
        """
        username = data.get('username')
        email = data.get('email')
        errors = {}

        user = User.objects.filter(
            Q(username=username) | Q(email=email)
        ).first()

        if user:
            if user.username != username:
                errors["email"] = [
                    "Это имя пользователя(ник) уже используется в системе."
                ]
            if user.email != email:
                errors["username"] = [
                    "Пользователь с таким email уже зарегистрирован в системе."
                ]

        if errors:
            raise serializers.ValidationError(errors)
        return data
    
    def create(self, validated_data):
        """
        Создает пользователя.
        """
        user = User(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user


class TokenSerializer(serializers.Serializer):
    """Сериализатор для получения токена."""
    email = serializers.EmailField(max_length=MAX_LENGTH_254, required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        """
        Проверяем данные для указанного пользователя.
        """
        email = data.get('email')
        password = data.get('password')
        user = User.objects.filter(email=email).first()
        if user is None or not user.check_password(password):
            raise serializers.ValidationError('Invalid credentials')
        return data


class TagSerializer(serializers.Serializer):
    id=serializers.PrimaryKeyRelatedField(read_only=True)
    name = serializers.CharField(read_only=True)
    slug = serializers.SlugField(read_only=True)

    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientRecipeSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(source='ingredient.id', read_only=True)
    amount = serializers.IntegerField()

    class Meta:
        model = IngredientRecipe
        fields = ['id', 'amount']

    def validate_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("Количество не может быть отрицательным.")
        return value
    

class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class UserModelSerializer(serializers.ModelSerializer):
    """Сериализатор для UserModel."""

    email = serializers.EmailField(required=True)
    avatar = Base64ImageField(required=False, allow_null=True)
    is_subscribed = serializers.BooleanField(read_only=True, default=False)
    
    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name', 'is_subscribed', 'avatar')


class ChangePasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True)
    current_password = serializers.CharField(required=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Старый пароль неверен.")
        return value

    def validate_new_password(self, value):
        if len(value) < 8:  # !!! Добавить валидацию пароля
            raise serializers.ValidationError("Пароль должен содержать минимум 8 символов.")
        return value

class UserAvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True)
    # avatar = serializers.SerializerMethodField(
    #     'get_avatar_url',
    #     read_only=True,
    # )
    
    class Meta:
        model = User
        fields = ['avatar']

    # def get_avatar_url(self, obj):
    #     if obj.avatar:
    #         return obj.avatar.url
    #     return None
    

class RecipeSerializerForRead(serializers.ModelSerializer): 
    """Сериализатор для просмотра рецептов."""
    is_favorited = serializers.BooleanField(read_only=True, default=False)
    is_in_shopping_cart = serializers.BooleanField(read_only=True, default=False)
    author = serializers.SlugRelatedField(slug_field='username', read_only=True)
    ingredients = IngredientSerializer(required=False, many=True)
    image = Base64ImageField(required=False, allow_null=True)
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'name', 'cooking_time', 'ingredients',
            'text', 'author', 'image', 'is_favorited',
            'is_in_shopping_cart'
        )
        read_only_fields = ('author',)


class RecipeSerializer(serializers.ModelSerializer): 
    """Сериализатор для записи рецептов."""
    is_favorited = serializers.BooleanField(read_only=True, default=False)
    is_in_shopping_cart = serializers.BooleanField(read_only=True, default=False)
    author = serializers.SlugRelatedField(slug_field='username', read_only=True)
    ingredients = IngredientRecipeSerializer(many=True)
    image = Base64ImageField(required=False, allow_null=True)
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'name', 'cooking_time', 'ingredients',
            'text', 'author', 'image', 'is_favorited',
            'is_in_shopping_cart'
        )
        read_only_fields = ('author',)

    def add_tags_ingredients(self, ingredients, tags, recipe):
        for ingredient in ingredients:
            try:
                current_ingredient = Ingredient.objects.get(id=ingredient['id'])
            except Ingredient.DoesNotExist:
                raise serializers.ValidationError(f"Ингредиент с id {ingredient['id']} не найден.")
            amount = ingredient['amount']
            if amount is None or int(amount) < 0:
                raise serializers.ValidationError("Количество должно быть не отрицательным.")
            IngredientRecipe.objects.create(
                    recipe=recipe,
                    ingredient=current_ingredient,
                    amount=amount
                )
            recipe.tags.set(tags)

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        self.add_tags_ingredients(ingredients, tags, recipe)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients')
        self.ingredients.clear() # возможно тут надо instanse
        tags = validated_data.pop('tags') 
        # self.tags.clear() 
        self.add_tags_ingredients(ingredients, tags, instance)
        return super().update(instance, validated_data)
