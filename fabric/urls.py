from django.urls import path
from fabric.views import towns, towns_delete, factory

urlpatterns = [
    path('towns/', towns, name='towns'),
    path('towns/<int:pk>/', towns_delete, name='towns-delete'),
    path('factory/', factory, name='factory'),
]
