"""backend_footgram URL Configuration"""

from recipes.views import IngredientViewSet, RecipeViewSet, UserModelViewSet, TokenView, TagViewSet
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
    path('api/', include(router.urls)),
    path('api/auth/token/login/', TokenView.as_view(), name='token_login'),
    path('api/auth/token/logout/', TokenDestroyView.as_view(), name='token_logout'),
    path('api/users/me/avatar/', UserModelViewSet.as_view({'put': 'update_avatar', 'delete': 'destroy_avatar'})),
] 

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
