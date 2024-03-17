import datetime

from django.shortcuts import render
from django.http import HttpRequest
from .forms import DistributionForm
from .models import FactoryPoint, Sympathizer
from person.models import Person
# Create your views here.

def my_distribution(request: HttpRequest):
    if request.method == 'GET':
        return render(request, 'press/all_distribution.html', {})


def new_distrib(request: HttpRequest):
    if request.method == 'GET':
        form = DistributionForm(initial={
            'distribution_date': datetime.date.today().strftime('%Y-%m-%d'),
            'start_time': (datetime.datetime.now() - datetime.timedelta(minutes=60)).strftime("%H:%M"),
            'end_time': datetime.datetime.now().strftime("%H:%M"),
        })

        party_members = Person.objects.filter(party_member=True).order_by('last_name').all()
        sympathizers = Sympathizer.objects.all()
        return render(request, 'press/new-distrib.html', {
            'form': form,
            'party_members': party_members,
            'sympathizers': sympathizers
        })
    elif request.method == 'POST':
        pass