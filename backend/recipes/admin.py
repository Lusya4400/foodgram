"""Настройка панели администратора."""
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import Tag, Ingredient, Recipe, IngredientRecipe

User = get_user_model()


@admin.register(User)
class UserModelAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name')
    search_fields = ('username', 'email')
    ordering = ('username',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('name',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)
    list_filter = ('name',)


class IngredientInLine(admin.TabularInline):
    model = IngredientRecipe
    extra = 1
    min_num = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'get_favorite_count')
    search_fields = ('name', 'author')
    list_filter = ('tags',)
    ordering = ('name',)

    inlines = [IngredientInLine]

    def get_favorite_count(self, obj):
        """Возвращает количество добавлений рецепта в избранное."""
        return obj.favorite.count()

    get_favorite_count.short_description = 'Количество добавлений в избранное'
