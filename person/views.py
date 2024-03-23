from django.shortcuts import render
from django.http import HttpRequest
# Create your views here.


def login(request: HttpRequest):
    return render(request, 'login.html', {
        'login_error': True
    })


def profile(request: HttpRequest):

    return render(request, 'person/profile.html')