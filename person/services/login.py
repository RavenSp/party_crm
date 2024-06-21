from person.models import Person
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django_htmx.http import retarget

__all__ = ['auth_user']


def auth_user(request: HttpRequest, email: str, password: str) -> HttpResponse:
    '''
    Функция для аутентификации пользователя и редиректа на страницу профиля. ы
    :param request:
    :param email:
    :param password:
    :return:
    '''
    user = authenticate(email=email, password=password)
    if user:
        login(request, user)
        return redirect(to='person:profile')
    return render(request, 'login.html', {'login_error': True})
