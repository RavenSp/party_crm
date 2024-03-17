from django.urls import path
from .views import my_distribution, new_distrib

urlpatterns = [
    path('', my_distribution, name='all'),
    path('new-distrib/', new_distrib, name='new-distrib')
]
