from django.shortcuts import render
from django.http import HttpRequest
from person.services.login import auth_user
# Create your views here.


def login(request: HttpRequest):
    if request.method == 'POST':
        return auth_user(request, email=request.POST.get('email', None),
                                       password=request.POST.get('password', None))
    return render(request, 'login.html', {})


def profile(request: HttpRequest):

    return render(request, 'person/profile.html')
