from django.urls import path
from .views import profile, login, logout_view


urlpatterns = [
    path('', profile, name='profile'),
    path("hx-login", login, name='hx-login'),
    path('logout/', logout_view, name='logout'),
]
