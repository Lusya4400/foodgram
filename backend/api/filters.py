import django_filters

from recipes.models import Recipe, Tag, Ingredient


class RecipeFilter(django_filters.FilterSet):
    """Фильтрация рецептов по автору, тегам, избранному, списку покупок."""

    autor = django_filters.CharFilter(
        field_name='author__id', lookup_expr='exact'
    )
    tags = django_filters.ModelMultipleChoiceFilter(
        field_name='tags__slug', queryset=Tag.objects.all(),
        to_field_name='slug', lookup_expr='exact'
    )

    is_favorited = django_filters.NumberFilter(method='filter_is_favorited')

    is_in_shopping_cart = django_filters.NumberFilter(
        method='filter_is_in_shopping_cart'
    )

    class Meta:
        model = Recipe
        fields = ('author', 'tags', 'is_favorited', 'is_in_shopping_cart')

    def filter_by_tags(self, queryset, name, value):
        return queryset.filter(tags__slug__in=value)

    def filter_is_favorited(self, queryset, name, value):
        request = self.request
        if request.user.is_authenticated:
            if value:
                return queryset.filter(favorite__user=request.user)
            else:
                return queryset.exclude(favorite__user=request.user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        request = self.request
        if request.user.is_authenticated:
            if value:
                return queryset.filter(shopping__user=request.user)
            else:
                return queryset.exclude(shopping__user=request.user)
        return queryset


class IngredientFilter(django_filters.FilterSet):
    """Класс фильтрации для ингредиентов."""
    name = django_filters.CharFilter(
        field_name='name', lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ('name',)
