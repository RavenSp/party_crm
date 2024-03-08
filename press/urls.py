
from django.urls import path
from .views import my_distribution
urlpatterns = [
    path('', my_distribution, name='all')
]
