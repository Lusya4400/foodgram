from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import UserModel, Tag, Ingredient, Recipe, Favorite

@admin.register(UserModel)
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
    list_filter = ('name',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'get_favorite_count')
    search_fields = ('name', 'author')
    list_filter = ('tags',)
    ordering = ('name',)

    def get_favorite_count(self, obj):
        """Возвращает количество добавлений рецепта в избранное."""
        return obj.favorite.count()

    get_favorite_count.short_description = 'Количество добавлений в избранное'