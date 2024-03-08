import datetime

from django.shortcuts import render
from django.http import HttpRequest
from .forms import DistributionForm
from .models import FactoryPoint
# Create your views here.

def my_distribution(request: HttpRequest):
    factories = FactoryPoint.objects.filter()
    form = DistributionForm(initial={
        'distribution_date': datetime.date.today().strftime('%Y-%m-%d'),
        'start_time': datetime.datetime.now().strftime("%H:%M"),
        'end_time': (datetime.datetime.now() + datetime.timedelta(minutes=60)).strftime("%H:%M"),
    })
    return render(request, 'press/all_distribution.html', {'form': form})