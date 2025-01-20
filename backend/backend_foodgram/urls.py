"""backend_foodgram URL Configuration"""

from recipes.views import (
    IngredientViewSet, RecipeViewSet, UserModelViewSet, TokenView,
    TagViewSet, RecipeLinkView, FollowViewSet, FavoriteViewSet,
    RecipeDetailView, ShoppingCartViewSet)
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from djoser.views import TokenDestroyView
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'recipes', RecipeViewSet)
router.register(r'tags', TagViewSet)
router.register(r'ingredients', IngredientViewSet)
router.register(r'users', UserModelViewSet, basename='users')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/subscriptions/',
         FollowViewSet.as_view({'get': 'list'}),
         name='subscriptions'),
    path('api/recipes/download_shopping_cart/',
         ShoppingCartViewSet.as_view({'get': 'download_shopping_list'}),
         name='shopping_list'),
    path('api/', include(router.urls)),
    path('api/auth/token/login/', TokenView.as_view(), name='token_login'),
    path('api/auth/token/logout/',
         TokenDestroyView.as_view(), name='token_logout'),
    path('api/users/me/avatar/',
         UserModelViewSet.as_view({
             'put': 'update_avatar',
             'delete': 'destroy_avatar'
         })),
    path('api/recipes/<int:id>/get-link/', RecipeLinkView.as_view(),
         name='recipe-link'),
    path('api/users/<int:id>/subscribe/',
         FollowViewSet.as_view({'post': 'create', 'delete': 'destroy'}),
         name='subscribe'),
    path('api/recipes/<int:id>/favorite/',
         FavoriteViewSet.as_view({'post': 'create', 'delete': 'destroy'}),
         name='favorite'),
    path('api/recipes/<int:id>/shopping_cart/',
         ShoppingCartViewSet.as_view({'post': 'create', 'delete': 'destroy'}),
         name='shopping'),
    path('s/<int:code>/',
         RecipeDetailView.as_view(), name='recipe_detail')
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
