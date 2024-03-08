from django.shortcuts import render
from django.http import HttpRequest
# Create your views here.


def profile(request: HttpRequest):

    return render(request, 'person/profile.html')