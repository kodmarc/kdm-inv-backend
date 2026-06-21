from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ItemCategoryViewSet, ItemViewSet

router = DefaultRouter()
router.register('item-categories', ItemCategoryViewSet, basename='item-category')
router.register('items', ItemViewSet, basename='item')

urlpatterns = [
    path('', include(router.urls)),
]
