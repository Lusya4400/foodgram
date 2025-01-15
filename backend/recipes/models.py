from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password
# from django.contrib.auth import get_user_model
from django.db import models
from django.core.exceptions import ValidationError

from .validators import validate_username

# User = get_user_model()
MAX_LENGTH_150 = 150
MAX_LENGTH_254 = 254

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
        default=None
    )

    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']


    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['username']

    def __str__(self):
        return str(self.username)

class Ingredient(models.Model):
    name = models.CharField(max_length=64)
    measurement_unit = models.CharField(max_length=64)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=64)
    slug = models.SlugField(max_length=12)

    def __str__(self):
        return self.name


class Recipe(models.Model):
    name = models.CharField(max_length=100)
    text = models.CharField(max_length=256)
    is_favorited = models.BooleanField(default=False)
    is_in_shopping_cart = models.BooleanField(default=False)
    cooking_time = models.IntegerField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='recipes',
        on_delete=models.CASCADE
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
        default=None
    )
    created = models.DateTimeField(
        'Дата добавления', auto_now_add=True, db_index=True
    )

    class Meta:
        ordering = ['-created']
    
    def __str__(self):
        return self.name


class IngredientRecipe(models.Model):
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    amount = models.IntegerField()

    def __str__(self):
        return f'{self.recipe} {self.ingredient} {self.amount}'


class TagRecipe(models.Model):
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.recipe} {self.tag}'