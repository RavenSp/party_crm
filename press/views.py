from django.shortcuts import render
from django.http import HttpRequest
# Create your views here.

def my_distribution(request: HttpRequest):
    return render(request, 'press/all_distribution.html', {})