import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db.models import Q
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .conctans import MAX_LENGTH_150, MAX_LENGTH_254
from .models import (
    Favorite, Follow, Ingredient, IngredientRecipe, Recipe,
    ShoppingCart, Tag)
from .validators import validate_username

User = get_user_model()


class SignupSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации пользователя."""
    email = serializers.EmailField(max_length=MAX_LENGTH_254, required=True)
    username = serializers.CharField(
        max_length=MAX_LENGTH_150,
        required=True,
        validators=[validate_username],
    )
    first_name = serializers.CharField(
        max_length=MAX_LENGTH_150, required=True)
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
        Проверка пользователя в базе данных.
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
        Создание пользователя.
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
        Проверка данных для указанного пользователя.
        """
        email = data.get('email')
        password = data.get('password')
        user = User.objects.filter(email=email).first()
        if user is None or not user.check_password(password):
            raise serializers.ValidationError('Invalid credentials')
        return data


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов."""
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов."""
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientRecipeSerializerForUpdate(serializers.Serializer):
    """Сериализатор для получения ингредиентов.

    Предназначен для обновления состава ингредиентов в рецепте."""
    id = serializers.IntegerField()
    amount = serializers.IntegerField()

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'amount')


class IngredientRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов в рецепте."""
    id = serializers.PrimaryKeyRelatedField(
        source='ingredient.id', read_only=True)
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit', read_only=True)

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class Base64ImageField(serializers.ImageField):
    """Сериализатор для кодировки изображений."""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class UserModelSerializer(serializers.ModelSerializer):
    """Сериализатор для модели пользователя."""
    email = serializers.EmailField(required=True)
    avatar = Base64ImageField(required=False, allow_null=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar'
        )

    def get_is_subscribed(self, obj):
        """Получение данных о наличии подписки на этого пользователя."""
        request = self.context.get('request')
        user = self.context['request'].user if request else None
        if user and user.is_authenticated:
            return Follow.objects.filter(user=user, following=obj).exists()
        return False


class ChangePasswordSerializer(serializers.Serializer):
    """Сериализатор для смены пароля."""
    new_password = serializers.CharField(required=True)
    current_password = serializers.CharField(required=True)

    def validate_current_password(self, value):
        """Проверка старого пароля."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Старый пароль неверен.")
        return value

    def validate_new_password(self, value):
        """Проверка нового пароля."""
        if len(value) < 8:
            raise serializers.ValidationError(
                "Пароль должен содержать минимум 8 символов.")
        return value


class UserAvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для аватара пользователя."""
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ['avatar']


class RecipeSerializerForRead(serializers.ModelSerializer):
    """Сериализатор для просмотра рецептов."""
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    author = UserModelSerializer()
    ingredients = IngredientRecipeSerializer(
        many=True, source='ingredientrecipe_set'
    )
    image = Base64ImageField(required=False, allow_null=True)
    tags = TagSerializer(many=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time',
        )
        read_only_fields = ('author',)

    def get_is_favorited(self, obj):
        """Получение данных о наличие рецепта в списке избранного."""
        request = self.context.get('request')
        user = request.user if request else None
        if user and user.is_authenticated:
            return Favorite.objects.filter(user=user, recipe=obj).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        """Получение данных о наличие рецепта в списке покупок."""
        request = self.context.get('request')
        user = request.user if request else None
        if user and user.is_authenticated:
            return ShoppingCart.objects.filter(user=user, recipe=obj).exists()
        return False


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для записи рецептов."""
    author = serializers.SlugRelatedField(
        slug_field='username', read_only=True
    )
    ingredients = IngredientRecipeSerializerForUpdate(many=True)
    image = Base64ImageField(required=False, allow_null=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )

    class Meta:
        model = Recipe
        fields = (
            'tags', 'name', 'cooking_time', 'ingredients',
            'text', 'author', 'image'
        )
        read_only_fields = ('author',)

    def validate(self, data):
        """Проверка данных для создания или обновления рецепта."""
        ingredients = data.get('ingredients')
        tags = data.get('tags')
        cooking_time = data.get('cooking_time')

        if cooking_time is None or cooking_time < 1:
            raise serializers.ValidationError(
                "Время приготовления не может быть меньше 1.")
        if ingredients is None or len(ingredients) == 0:
            raise serializers.ValidationError(
                "Список ингредиентов не может быть пустым.")
        for ingredient in ingredients:
            if not ingredient.get('id') or not ingredient.get('amount'):
                raise serializers.ValidationError(
                    "Указание ингредиента и количества обязательно.")
            try:
                Ingredient.objects.get(id=ingredient['id'])
            except Ingredient.DoesNotExist:
                raise serializers.ValidationError(
                    f"Ингредиент с id {ingredient['id']} не найден.")
            amount = ingredient['amount']
            if amount is None or int(amount) <= 0:
                raise serializers.ValidationError(
                    "Количество ингредиентов должно быть положительным."
                    f"Ингредиент с id {ingredient['id']}")
        ingredients_id = [ingredient['id'] for ingredient in ingredients]
        if len(ingredients_id) != len(set(ingredients_id)):
            raise serializers.ValidationError(
                "Ингредиенты должны быть уникальными.")
        if tags is None or len(tags) == 0:
            raise serializers.ValidationError("Теги не могут быть пустыми.")
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError("Теги должны быть уникальными.")
        return data

    def add_ingredients_tags(self, ingredients, tags, recipe):
        """Установка тегов и ингредиентов для рецепта."""
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
        """Создание рецепта."""
        if 'image' not in validated_data:
            raise serializers.ValidationError(
                "Необходимо добавить картинку для рецепта.")
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        self.add_ingredients_tags(ingredients, tags, recipe)
        return recipe

    def update(self, instance, validated_data):
        """Обновление рецепта."""
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

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'image', 'cooking_time'
        )


class UserSerializerForSubscribe(UserModelSerializer):
    """Сериализатор для модели пользователя в подписке.

    Добавляет информацию о количестве рецептов.
    """
    is_subscribed = serializers.BooleanField(read_only=True, default=True)
    recipes = RecipeSerializerForSubscribe(many=True)
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count', 'avatar')

    def get_recipes_count(self, obj):
        """Метод для подсчёта количества рецептов у пользователя."""
        return obj.recipes.count()


class FollowSerializer(serializers.ModelSerializer):
    """Сериализатор для подписок."""
    user = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True,
        default=serializers.CurrentUserDefault()
    )
    following = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

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

    def validate_following(self, value):
        """Проверка данных подписки."""
        if value == self.context['request'].user:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя!'
            )
        return value

    def to_representation(self, instance):
        """Формирование ответа."""
        return UserSerializerForSubscribe(instance.following).data


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для избранных рецептов."""
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
    """Сериализатор для списка покупок."""
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
