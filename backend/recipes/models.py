import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model
from django.db import models

from .conctans import (
    MAX_LENGTH_32, MAX_LENGTH_64, MAX_LENGTH_100, MAX_LENGTH_128,
    MAX_LENGTH_150, MAX_LENGTH_254, MAX_LENGTH_256
)
from .validators import validate_username


class UserModel(AbstractUser):
    """Кастомная модель пользователя."""
    username = models.CharField(
        max_length=MAX_LENGTH_150,
        unique=True,
        validators=[validate_username],
        verbose_name='Никнейм'
    )
    email = models.EmailField(
        max_length=MAX_LENGTH_254,
        unique=True,
        verbose_name='Email'
    )
    first_name = models.CharField(
        max_length=MAX_LENGTH_150,
        verbose_name='Имя'
    )
    last_name = models.CharField(
        max_length=MAX_LENGTH_150,
        verbose_name='Фамилия'
    )
    avatar = models.ImageField(
        upload_to='recipes/avatars/',
        null=True,
        default=None,
        verbose_name='Аватар'
    )

    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['username']

    def __str__(self):
        return str(self.username)


User = get_user_model()


class Ingredient(models.Model):
    """Модель для ингредиентов."""
    name = models.CharField(
        max_length=MAX_LENGTH_128,
        verbose_name='Наименование'
    )
    measurement_unit = models.CharField(
        max_length=MAX_LENGTH_64,
        verbose_name='Единица измерения'
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name


class Tag(models.Model):
    """Модель для тегов."""
    name = models.CharField(
        max_length=MAX_LENGTH_32,
        verbose_name='Наименование'
    )
    slug = models.SlugField(
        max_length=MAX_LENGTH_32,
        verbose_name='Слаг'
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Модель для рецептов."""
    name = models.CharField(
        max_length=MAX_LENGTH_100,
        verbose_name='Наименование'
    )
    text = models.CharField(
        max_length=MAX_LENGTH_256,
        verbose_name='Порядок приготовления'
    )
    cooking_time = models.IntegerField(
        verbose_name='Время приготовления'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='recipes',
        on_delete=models.CASCADE,
        verbose_name='Автор'
    )
    tags = models.ManyToManyField(
        Tag, through='TagRecipe'
    )
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
    code = models.CharField(max_length=10, unique=True, default='')

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ['-created']

    def __str__(self):
        return self.name

    @staticmethod
    def generate_code():
        return str(uuid.uuid4().int)[:10]

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_code()
        super().save(*args, **kwargs)


class IngredientRecipe(models.Model):
    """Модель для связи ингредиентов с рецептами."""
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    amount = models.IntegerField()

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


class Favorite(models.Model):
    """Модель для избранных рецептов."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='favorite')
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='favorite')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='user_recipe'
            ),
        ]


class ShoppingCart(models.Model):
    """Модель для списка покупок."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='shopping')
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='shopping')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='user_recipe_shopping'
            ),
        ]
