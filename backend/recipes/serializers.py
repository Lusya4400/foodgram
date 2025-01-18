import base64
import datetime as dt
import logging

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db.models import Q
from rest_framework import serializers

from .models import Ingredient, IngredientRecipe, Recipe, Tag, Follow, Favorite, ShoppingCart
from .validators import validate_username
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.validators import UniqueTogetherValidator
from rest_framework_simplejwt.tokens import RefreshToken

MAX_LENGTH_150 = 150
MAX_LENGTH_254 = 254

User = get_user_model()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

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


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientRecipeSerializerForUpdate(serializers.Serializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField()

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'amount')


class IngredientRecipeSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(source='ingredient.id', read_only=True)
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(source='ingredient.measurement_unit', read_only=True)
    # amount = serializers.IntegerField()

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')

    # def validate_amount(self, value):
    #     if value < 0:
    #         raise serializers.ValidationError("Количество не может быть отрицательным.")
    #     return value


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
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name', 'is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        user = self.context['request'].user if request else None
        if user and user.is_authenticated:
            return Follow.objects.filter(user=user, following=obj).exists()
        return False


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
    # is_favorited = serializers.BooleanField(read_only=True, default=False)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    author = UserModelSerializer()
    ingredients = IngredientRecipeSerializer(many=True, source='ingredientrecipe_set')
    image = Base64ImageField(required=False, allow_null=True)
    tags = TagSerializer(many=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author',  'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time',
        )
        read_only_fields = ('author',)

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        if user and user.is_authenticated:
            return Favorite.objects.filter(user=user, recipe=obj).exists()
        return False
    
    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        if user and user.is_authenticated:
            return ShoppingCart.objects.filter(user=user, recipe=obj).exists()
        return False


class RecipeSerializer(serializers.ModelSerializer): 
    """Сериализатор для записи рецептов."""
    # is_favorited = serializers.BooleanField(read_only=True, default=True)
    # is_in_shopping_cart = serializers.BooleanField(read_only=True, default=True)
    author = serializers.SlugRelatedField(slug_field='username', read_only=True)
    ingredients = IngredientRecipeSerializerForUpdate(many=True)
    image = Base64ImageField(required=False, allow_null=True)
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True)

    class Meta:
        model = Recipe
        fields = (
            'tags', 'name', 'cooking_time', 'ingredients',
            'text', 'author', 'image'
        )
        read_only_fields = ('author',)

    def validate(self,data):
        ingredients = data.get('ingredients')
        tags = data.get('tags')
        cooking_time = data.get('cooking_time')

        if cooking_time is None or cooking_time < 1:
            raise serializers.ValidationError("Время приготовления не может быть меньше 1.")
        if ingredients is None or len(ingredients) == 0:
            raise serializers.ValidationError("Список ингредиентов не может быть пустым.")
        for ingredient in ingredients:
            if not ingredient.get('id') or not ingredient.get('amount'):
                raise serializers.ValidationError("Указание ингредиента и количества обязательно.")
            try:
                Ingredient.objects.get(id=ingredient['id'])
            except Ingredient.DoesNotExist:
                raise serializers.ValidationError(f"Ингредиент с id {ingredient['id']} не найден.")
            amount = ingredient['amount']
            if amount is None or int(amount) <= 0:
                raise serializers.ValidationError("Количество ингредиентов должно быть положительным."
                                                  f"Ингредиент с id {ingredient['id']}")
        ingredients_id = [ingredient['id'] for ingredient in ingredients]
        if len(ingredients_id) != len(set(ingredients_id)):
            raise serializers.ValidationError("Ингредиенты должны быть уникальными.")
        if tags is None or len(tags) == 0:
            raise serializers.ValidationError("Теги не могут быть пустыми.")
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError("Теги должны быть уникальными.")
        return data

    # def add_ingredients(self, ingredients, recipe):
    #     for ingredient in ingredients:
    #         try:
    #             current_ingredient = Ingredient.objects.get(id=ingredient['id'])
    #         except Ingredient.DoesNotExist:
    #             raise serializers.ValidationError(f"Ингредиент с id {ingredient['id']} не найден.")
    #         amount = ingredient['amount']
    #         if amount is None or int(amount) <= 0:
    #             raise serializers.ValidationError("Количество должно быть положительным.")
    #         IngredientRecipe.objects.create(
    #                 recipe=recipe,
    #                 ingredient=current_ingredient,
    #                 amount=amount
    #            )
    def add_ingredients_tags(self, ingredients, tags, recipe):
        for ingredient in ingredients:
            current_ingredient = Ingredient.objects.get(id=ingredient['id'])
            amount = ingredient['amount']
            IngredientRecipe.objects.create(
                    recipe=recipe,
                    ingredient=current_ingredient,
                    amount=amount
                )
        recipe.tags.set(tags)

    def create(self, validated_data):
        if 'image' not in validated_data:
            raise serializers.ValidationError("Необходимо добавить картинку для рецепта.")
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        self.add_ingredients_tags(ingredients, tags, recipe)
        return recipe

#!!! Изменить проверки ДОбавляется несуществующий ингредиент и с 0 количеством
    # def create(self, validated_data):
    #     if validated_data.get('cooking_time') < 1:
    #         raise serializers.ValidationError("Время приготовления не может быть меньше 1.")
    #     if 'image' not in validated_data:
    #         raise serializers.ValidationError("Необходимо добавить картинку для рецепта.")
    #     ingredients = validated_data.pop('ingredients')
    #     if ingredients is None or len(ingredients) == 0:
    #         raise serializers.ValidationError("Список ингредиентов не может быть пустым.")
    #     ingredients_id = [ingredient['id'] for ingredient in ingredients]
    #     if len(ingredients_id) != len(set(ingredients_id)):
    #         raise serializers.ValidationError("Ингредиенты должны быть уникальными.")
    #     tags = validated_data.pop('tags')
    #     if tags is None or len(tags) == 0:
    #         raise serializers.ValidationError("Теги не могут быть пустыми.")
    #     if len(tags) != len(set(tags)):
    #         raise serializers.ValidationError("Теги должны быть уникальными.")
    #     recipe = Recipe.objects.create(**validated_data)
    #     self.add_ingredients(ingredients, recipe)
    #     recipe.tags.set(tags)
    #     return recipe

    # def update(self, instance, validated_data):

    #     if validated_data.get('cooking_time') < 1:
    #         raise serializers.ValidationError("Время приготовления не может быть меньше 1.")
    #     ingredients = validated_data.pop('ingredients', None)
    #     if ingredients is None or len(ingredients) == 0:
    #         raise serializers.ValidationError("Список ингредиентов не может быть пустым.")
    #     ingredients_id = [ingredient['id'] for ingredient in ingredients]
    #     if len(ingredients_id) != len(set(ingredients_id)):
    #         raise serializers.ValidationError("Ингредиенты должны быть уникальными.") 
    #     tags = validated_data.pop('tags', None)
    #     if tags is None or len(tags) == 0:
    #         raise serializers.ValidationError("Теги не могут быть пустыми.")
    #     if len(tags) != len(set(tags)):
    #         raise serializers.ValidationError("Теги должны быть уникальными.")
    #     instance.ingredientrecipe_set.all().delete()
    #     self.add_ingredients(ingredients, instance)
    #     instance.tags.set(tags)
    #     return super().update(instance, validated_data)
    
    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients', None)
        tags = validated_data.pop('tags', None)
        instance.ingredientrecipe_set.all().delete()
        self.add_ingredients_tags(ingredients, tags, instance)
        return super().update(instance, validated_data)
    
    def to_representation(self, instance):
        """Формирование ответа с использованием RecipeSerializerForRead."""
        return RecipeSerializerForRead(instance).data


class RecipeSerializerForSubscribe(RecipeSerializerForRead): 
    """Сериализатор для просмотра подписок."""
   # image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'image','cooking_time',
        )
  #      read_only_fields = ('author',)


class UserSerializerForSubscribe(UserModelSerializer):
    """Сериализатор для UserModel в подписке.
    
    Добавляем информацию о количестве рецептов и установку ограничения
    на количество выводимых рецептов у пользователя.
    """
    is_subscribed = serializers.BooleanField(read_only=True, default=True)
    recipes = RecipeSerializerForSubscribe(many=True)
    # recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count', 'avatar')

    def get_recipes_count(self, obj):
        """Метод для подсчёта количества рецептов у пользователя."""
        return obj.recipes.count()

    # def get_recipes(self, obj):
    #     """Метод для ограничения количества рецептов пользователя.

    #     Используем параметр recipes_limit.
    #     """
    #     logger.debug(f'Validated {self.context.get("request")}')
    #     request = self.context.get('request')
    #     recipes_limit = request.query_params.get('recipes_limit') if request else None

    #     recipes_query = obj.recipes.all()
    #     if recipes_limit:
    #         recipes_query = recipes_query[:int(recipes_limit)]

    #     recipes_data = RecipeSerializerForSubscribe(recipes_query, many=True).data

    #     fields_to_include = ['id', 'name', 'image', 'cooking_time']
    #     filtered_recipes = [
    #         {field: recipe.get(field) for field in fields_to_include}
    #         for recipe in recipes_data
    #     ]

    #     return filtered_recipes
    

class FollowSerializer(serializers.ModelSerializer): 
    user = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True,
        default=serializers.CurrentUserDefault()
    ) 

    following = serializers.PrimaryKeyRelatedField(queryset=User.objects.all()) 
    #following = serializers.SerializerMethodField(required=False, read_only=True)
  #  following = serializers.SlugRelatedField(slug_field='username', queryset=User.objects.all())

#     )
#   #  following = user

    class Meta: 
        model = Follow 
        fields = ('user', 'following') 
        validators = [ 
            UniqueTogetherValidator( 
                queryset=Follow.objects.all(), 
                fields=('user', 'following'), 
                message='Такая подписка уже существует.' 
            )
        ] 

    # def get_following(self, obj):
    #     logger.debug(f'Validated {self.context.get("request")}')
    #     request = self.context.get('request')
    #     following_id = request.query_params.get('id') if request else None
    #     try:
    #         following = User.objects.get(id=following_id)
    #     except User.DoesNotExist:
    #         raise serializers.ValidationError(f"Пользователь не найден.")
    #     return following
    
    def validate_following(self, value):
        if value == self.context['request'].user:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя!'
            )
        return value
    
    def to_representation(self, instance):
        """Формирование ответа."""
        return UserSerializerForSubscribe(instance.following).data


class FavoriteSerializer(serializers.ModelSerializer): 
    user = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True,
        default=serializers.CurrentUserDefault()
    ) 

    recipe = serializers.PrimaryKeyRelatedField(queryset=Recipe.objects.all()) 

    class Meta: 
        model = Favorite
        fields = ('user', 'recipe') 
        validators = [ 
            UniqueTogetherValidator( 
                queryset=Favorite.objects.all(), 
                fields=('user', 'recipe'), 
                message='Этот рецепт уже добавлен в избранное.' 
            )
        ] 

    
    def to_representation(self, instance):
        """Формирование ответа."""
        return RecipeSerializerForSubscribe(instance.recipe).data


class ShoppingCartSerializer(serializers.ModelSerializer): 
    user = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True,
        default=serializers.CurrentUserDefault()
    ) 

    recipe = serializers.PrimaryKeyRelatedField(queryset=Recipe.objects.all()) 

    class Meta: 
        model = ShoppingCart
        fields = ('user', 'recipe') 
        validators = [ 
            UniqueTogetherValidator( 
                queryset=ShoppingCart.objects.all(), 
                fields=('user', 'recipe'), 
                message='Этот рецепт уже добавлен в список покупок.' 
            )
        ] 

    
    def to_representation(self, instance):
        """Формирование ответа."""
        return RecipeSerializerForSubscribe(instance.recipe).data
    

        # logger.debug(f'Validated {validated_data}')
        # logger.debug(f'Instance: {instance}')