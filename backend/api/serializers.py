import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import (
    Favorite, Follow, Ingredient, IngredientRecipe, Recipe,
    ShoppingCart, Tag)

User = get_user_model()


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

    def validate(self, data):
        """Проверка данных ингредиентов."""
        ingredient_id = data.get('id')
        try:
            Ingredient.objects.get(id=ingredient_id)
        except Ingredient.DoesNotExist:
            raise serializers.ValidationError(
                f"Ингредиент с id {ingredient_id} не найден.")
        amount = data.get('amount')
        if amount is None or int(amount) <= 0:
            raise serializers.ValidationError(
                "Количество ингредиентов должно быть положительным."
            )
        return data


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
        return bool(
            request and request.user.is_authenticated
            and Follow.objects.filter(user=request.user, following=obj)
        )


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
        return bool(
            request and request.user.is_authenticated
            and Favorite.objects.filter(user=request.user, recipe=obj).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        """Получение данных о наличие рецепта в списке покупок."""
        request = self.context.get('request')
        return bool(
            request and request.user.is_authenticated
            and ShoppingCart.objects.filter(
                user=request.user, recipe=obj).exists()
        )


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для записи рецептов."""
    author = serializers.SlugRelatedField(
        slug_field='username', read_only=True
    )
    ingredients = IngredientRecipeSerializerForUpdate(many=True)
    image = Base64ImageField(required=True, allow_null=True)
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
        if ingredients is None or len(ingredients) == 0:
            raise serializers.ValidationError(
                "Список ингредиентов не может быть пустым.")
        for ingredient in ingredients:
            if not ingredient.get('id') or not ingredient.get('amount'):
                raise serializers.ValidationError(
                    "Указание ингредиента и количества обязательно.")
        ingredients_id = [ingredient['id'] for ingredient in ingredients]
        if len(ingredients_id) != len(set(ingredients_id)):
            raise serializers.ValidationError(
                "Ингредиенты должны быть уникальными.")
        if tags is None or len(tags) == 0:
            raise serializers.ValidationError("Теги не могут быть пустыми.")
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError("Теги должны быть уникальными.")
        return data

    def validate_image(self, value):
        """Проверка наличия картинки для рецепта."""
        if value is None:
            raise serializers.ValidationError(
                "Необходимо добавить картинку для рецепта.")
        return value

    @staticmethod
    def add_ingredients_tags(ingredients, tags, recipe):
        """Установка тегов и ингредиентов для рецепта."""
        IngredientRecipe.objects.bulk_create([
            IngredientRecipe(
                recipe=recipe, ingredient_id=ingredient['id'],
                amount=ingredient['amount']
            ) for ingredient in ingredients]
        )
        recipe.tags.set(tags)

    def create(self, validated_data):
        """Создание рецепта."""
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


class UserSerializerForReadSubscribe(UserModelSerializer):
    """Сериализатор для отображения подписок.

    Добавляет информацию о количестве рецептов.
    """
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = UserModelSerializer.Meta.fields + ('recipes', 'recipes_count')

    def get_recipes_count(self, obj):
        """Метод для подсчёта количества рецептов у пользователя."""
        return obj.recipes.count()

    def get_recipes(self, obj):
        """
        Метод для получения рецептов с ограничением по числу,
        используя параметр recipes_limit.
        """
        recipes_limit = self.context.get('request').query_params.get(
            'recipes_limit')

        recipes_query = obj.recipes.all()
        if recipes_limit:
            recipes_query = recipes_query[:int(recipes_limit)]

        recipes_data = RecipeSerializerForSubscribe(
            recipes_query, many=True).data

        fields_to_include = ['id', 'name', 'image', 'cooking_time']
        filtered_recipes = [
            {field: recipe.get(field) for field in fields_to_include}
            for recipe in recipes_data
        ]
        return filtered_recipes


class FollowSerializer(serializers.ModelSerializer):
    """Сериализатор для записи подписок."""
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
        return UserSerializerForReadSubscribe(
            instance.following, context=self.context).data


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для избранных рецептов."""
    # При удалении поля user вылетает ошибка "user": "Обязательное поле."
    user = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True,
        default=serializers.CurrentUserDefault()
    )

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
        read_only_fields = ('user',)

    def to_representation(self, instance):
        """Формирование ответа."""
        return RecipeSerializerForSubscribe(instance.recipe).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для списка покупок."""
    # При удалении поля user вылетает ошибка "user": "Обязательное поле."
    user = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True,
        default=serializers.CurrentUserDefault()
    )

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
        read_only_fields = ('user',)

    def to_representation(self, instance):
        """Формирование ответа."""
        return RecipeSerializerForSubscribe(instance.recipe).data
