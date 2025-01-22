import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .constans import (
    LENGTH_SHORT_CODE, MIN_COOKING_TIME, MAX_SMAL_INTEGER_NUM,
    MIN_QUANTITY_INGREDIENT, MAX_LENGTH_SLAG, MAX_LENGTH_TAG,
    MAX_LENGTH_NAME_USER, MAX_LENGTH_INGREDIENT, MAX_LENGTH_RECIPE,
    MAX_LENGTH_USER, MAX_LENGTH_MEASHUREMENT_UNIT
)


class User(AbstractUser):
    """Кастомная модель пользователя."""
    username = models.CharField(
        max_length=MAX_LENGTH_USER,
        unique=True,
        validators=[UnicodeUsernameValidator()],
        verbose_name='Никнейм'
    )
    email = models.EmailField(
        unique=True,
        verbose_name='Email'
    )
    first_name = models.CharField(
        max_length=MAX_LENGTH_NAME_USER,
        verbose_name='Имя'
    )
    last_name = models.CharField(
        max_length=MAX_LENGTH_NAME_USER,
        verbose_name='Фамилия'
    )
    avatar = models.ImageField(
        upload_to='recipes/avatars/',
        null=True,
        default=None,
        verbose_name='Аватар'
    )

    USERNAME_FIELD = 'email'

    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['username']

    def __str__(self):
        return (
            f'{self.username}, {self.email}, {self.first_name},'
            f'{self.last_name}'
        )


class Ingredient(models.Model):
    """Модель для ингредиентов."""
    name = models.CharField(
        max_length=MAX_LENGTH_INGREDIENT,
        verbose_name='Наименование'
    )
    measurement_unit = models.CharField(
        max_length=MAX_LENGTH_MEASHUREMENT_UNIT,
        verbose_name='Единица измерения'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='name_measurement_unit'
            ),
        ]
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ['name']

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}'


class Tag(models.Model):
    """Модель для тегов."""
    name = models.CharField(
        max_length=MAX_LENGTH_TAG,
        verbose_name='Наименование'
    )
    slug = models.SlugField(
        max_length=MAX_LENGTH_SLAG,
        verbose_name='Слаг'
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ['name']

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Модель для рецептов."""
    name = models.CharField(
        max_length=MAX_LENGTH_RECIPE,
        verbose_name='Наименование'
    )
    text = models.TextField(
        verbose_name='Порядок приготовления'
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления',
        validators=[
            MinValueValidator(MIN_COOKING_TIME),
            MaxValueValidator(MAX_SMAL_INTEGER_NUM)
        ]
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='recipes',
        on_delete=models.CASCADE,
        verbose_name='Автор'
    )
    tags = models.ManyToManyField(Tag)
    ingredients = models.ManyToManyField(
        Ingredient, through='IngredientRecipe'
    )
    image = models.ImageField(
        upload_to='recipes/images/',
        null=True,
        default=None,
        verbose_name='Картинка'
    )
    created = models.DateTimeField(
        'Дата добавления', auto_now_add=True, db_index=True
    )
    short_code = models.CharField(
        max_length=LENGTH_SHORT_CODE, unique=True, default=''
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ['-created']

    def __str__(self):
        return f'{self.name}, {self.cooking_time}'

    @staticmethod
    def generate_code():
        while True:
            short_code = str(uuid.uuid4().int)[:LENGTH_SHORT_CODE]
            if not Recipe.objects.filter(short_code=short_code):
                return short_code

    def save(self, *args, **kwargs):
        if not self.short_code:
            self.short_code = self.generate_code()
        super().save(*args, **kwargs)


class IngredientRecipe(models.Model):
    """Модель для связи ингредиентов с рецептами."""
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество',
        validators=[
            MinValueValidator(MIN_QUANTITY_INGREDIENT),
            MaxValueValidator(MAX_SMAL_INTEGER_NUM)
        ]
    )

    def __str__(self):
        return f'{self.recipe} {self.ingredient} {self.amount}'


class TagRecipe(models.Model):
    """Модель для связи тегов с рецептами."""
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.recipe} {self.tag}'


class Follow(models.Model):
    """Модель для подписок на пользователей."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='following_user')
    following = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='following')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'following'],
                name='user_following'
            ),
            models.CheckConstraint(
                name="prevent_self_follow",
                check=~models.Q(user=models.F("following")),
            ),
        ]

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        ordering = ['user__username']

    def __str__(self):
        return (
            f'Пользователь {self.user.username}'
            f'подписан на {self.following.username}'
        )


class Favorite(models.Model):
    """Модель для избранных рецептов."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='user_recipe'
            ),
        ]
        default_related_name = 'favorite'
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные рецепты'
        ordering = ['user__username']


class ShoppingCart(models.Model):
    """Модель для списка покупок."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE
    )

    class Meta:
        default_related_name = 'shopping'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='user_recipe_shopping'
            ),
        ]
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Покупки'
        ordering = ['user__username']
