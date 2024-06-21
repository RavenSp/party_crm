from django.urls import path
from .views import profile, login


urlpatterns = [
    path('', profile, name='profile'),
    path("hx-login", login, name='hx-login')
]
