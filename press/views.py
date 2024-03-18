import datetime

from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from .forms import DistributionForm
from .models import FactoryPoint, Sympathizer
from helpers.common import name_normalizer
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

        party_members = Person.objects.filter(party_member=True).order_by('-last_name').all()
        sympathizers = Sympathizer.objects.all()
        return render(request, 'press/new-distrib.html', {
            'form': form,
            'party_members': party_members,
            'sympathizers': sympathizers
        })
    elif request.method == 'POST':
        pass


def new_party_member_distrib(request: HttpRequest):
    already_selected = request.POST.getlist('party-members')
    party_members = Person.objects.filter(party_member=True)
    if len([x for x in already_selected if x != '']) > 0:
        party_members = party_members.exclude(pk__in=[x for x in already_selected if x != ''])
    party_members = party_members.order_by('last_name').all()
    if len(party_members) == 0:
        return HttpResponse('', status='204')

    return render(request, 'press/party_member_field.html', context={'party_members': party_members})


def new_sympathizer_distrib(request: HttpRequest):
    already_selected = request.POST.getlist('sympathizer-members')
    print(already_selected)
    print([name_normalizer(x) for x in already_selected])
    sympathizers = Sympathizer.objects.order_by('name').all()
    if len([x for x in already_selected if x != '']) > 0:
        sympathizers = [x for x in sympathizers if x.normalize_name not in [name_normalizer(x) for x in already_selected if x != '']]

    return render(request, 'press/sypathizer_member_field.html', {'sympathizers': sympathizers})
