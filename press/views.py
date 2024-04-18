import datetime

from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .forms import DistributionForm
from .models import FactoryPoint, Sympathizer, NewspaperNumber
from helpers.common import name_normalizer
from person.models import Person
from press.services import distributions
from django.db import connection
# Create your views here.

@login_required()
def my_distribution(request: HttpRequest):
    if request.method == 'GET':
        distribs = distributions.get_all({'distribution_date__gte': (datetime.date.today() - datetime.timedelta(days=31)).strftime('%Y-%m-%d')})
        result = render(request, 'press/all_distribution.html', {'distribs': distribs})
        print(connection.queries)
        return result


@login_required()
def new_distrib(request: HttpRequest):
    if request.method == 'GET':
        form = DistributionForm(initial={
            'distribution_date': datetime.date.today().strftime('%Y-%m-%d'),
            'start_time': (datetime.datetime.now() - datetime.timedelta(minutes=60)).strftime("%H:%M"),
            'end_time': datetime.datetime.now().strftime("%H:%M"),
        })

        request.session['select_party_members'] = []
        party_members = Person.objects.filter(party_member=True).order_by('-last_name').all()
        sympathizers = Sympathizer.objects.all()
        newspapers = NewspaperNumber.objects.select_related('newspaper').order_by('year').all()
        return render(request, 'press/new-distrib.html', {
            'form': form,
            'party_members': party_members,
            'sympathizers': sympathizers,
            'newspapers': newspapers
        })
    elif request.method == 'POST':
        form = DistributionForm(request.POST)
        party_members = request.session.get('select_party_members', [])
        sympathizers = request.POST.getlist('sympathizer-members', [])
        newspapers = request.POST.getlist('newspaper', [])
        newspapers_quantity = request.POST.getlist('newspaper-quantity', [])
        error_list = []

        if len(party_members) + len(sympathizers) == 0:
            error_list.append('Должен быть хотя бы один раздающий!')

        if len(newspapers) == 0 or len(newspapers_quantity) == 0:
            error_list.append('Должна быть роздана хотя бы 1 газета')

        if len(newspapers) != len(newspapers_quantity):
            error_list.append('Некорректно введены данные о газетах!')

        if form.is_valid():
            pass
        else:
            form.errors


@login_required()
def new_party_member_distrib(request: HttpRequest):
    already_selected = request.POST.getlist('party-members')
    party_members = Person.objects.filter(party_member=True)
    if len([x for x in already_selected if x != '']) > 0:
        party_members = party_members.exclude(pk__in=[x for x in already_selected if x != ''])
    party_members = party_members.order_by('last_name').all()
    if len(party_members) == 0:
        return HttpResponse('', status='204')

    return render(request, 'press/party_member_field.html', context={'party_members': party_members})


@login_required()
def new_sympathizer_distrib(request: HttpRequest):
    already_selected = request.POST.getlist('sympathizer-members')
    print(already_selected)
    print([name_normalizer(x) for x in already_selected])
    sympathizers = Sympathizer.objects.order_by('name').all()
    if len([x for x in already_selected if x != '']) > 0:
        sympathizers = [x for x in sympathizers if
                        x.normalize_name not in [name_normalizer(x) for x in already_selected if x != '']]

    return render(request, 'press/sypathizer_member_field.html', {'sympathizers': sympathizers})


@login_required()
@require_http_methods(['DELETE'])
def hx_delete_party_member(request: HttpRequest, id_delete_member: int):
    select_party_members = set(request.session.get('select_party_members', []))
    if str(id_delete_member) not in select_party_members:
        return HttpResponse('', status='204')
    else:
        select_party_members.remove(str(id_delete_member))
    request.session['select_party_members'] = list(select_party_members)

    select_members = Person.objects.filter(pk__in=list(select_party_members)).all()
    not_select_members = Person.objects.exclude(pk__in=list(select_party_members)).all()

    return render(request, 'press/party_member_list2.html', {
        'select_members': select_members,
        'party_members': not_select_members
    })


@login_required()
@require_http_methods(['POST'])
def hx_add_party_member(request: HttpRequest):
    new_member = request.POST.get('select-party-members', None)
    if new_member is None:
        print("пустой ID")
        return HttpResponse('', status='204')
    select_party_members = set(request.session.get('select_party_members', []))
    select_party_members.add(str(new_member))
    request.session['select_party_members'] = list(select_party_members)

    select_members = Person.objects.filter(pk__in=list(select_party_members)).all()
    not_select_members = Person.objects.exclude(pk__in=list(select_party_members)).all()

    return render(request, 'press/party_member_list2.html', {
        'select_members': select_members,
        'party_members': not_select_members
    })


@login_required()
def hx_newspaper(request: HttpRequest):
    newspapers = NewspaperNumber.objects.select_related('newspaper').order_by('year').all()
    return render(request, 'press/newspapers_field.html', {'newspapers': newspapers})
