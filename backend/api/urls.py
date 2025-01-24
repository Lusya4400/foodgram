from django.urls import include, path
from .views import (
    IngredientViewSet, RecipeViewSet, UserModelViewSet,
    TagViewSet, RecipeLinkView)
from rest_framework import routers

router = routers.DefaultRouter()
router.register('recipes', RecipeViewSet)
router.register('tags', TagViewSet)
router.register('ingredients', IngredientViewSet)
router.register('users', UserModelViewSet, basename='users')

urlpatterns = [
    path('recipes/download_shopping_cart/',
         RecipeViewSet.as_view({'get': 'download_shopping_list'}),
         name='shopping_list'),
    path('auth/', include('djoser.urls.authtoken')),
    path('users/me/avatar/',
         UserModelViewSet.as_view({
             'put': 'update_avatar',
             'delete': 'destroy_avatar'
         }), name='me'),
    path('recipes/<int:id>/get-link/', RecipeLinkView.as_view(),
         name='recipe-link'),
    path('users/<int:id>/subscribe/',
         UserModelViewSet.as_view({
             'post': 'subscribe',
             'delete': 'unsubscribe'}), name='subscribe'),
    path('users/subscriptions/',
         UserModelViewSet.as_view({'get': 'subscriptions'}),
         name='subscriptions'),
    path('recipes/<int:id>/favorite/',
         RecipeViewSet.as_view({
             'post': 'favorite', 'delete': 'unfavorite'}), name='favorite'),
    path('recipes/<int:id>/shopping_cart/',
         RecipeViewSet.as_view({
             'post': 'add_to_cart',
             'delete': 'remove_from_cart'}), name='shopping'),

    path('', include(router.urls)),
]
