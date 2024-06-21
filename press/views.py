import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse, FileResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .forms import DistributionForm
from .models import FactoryPoint, Sympathizer, NewspaperNumber, NewspaperNumbersOnDistribution, \
    DistributionPartyMembers, DistributionSympathizerMember, Distribution
from helpers.common import name_normalizer
from person.models import Person
from press.services import distributions, report
from django.db import connection
from render_block import render_block_to_string
# Create your views here.


@login_required()
def my_distribution(request: HttpRequest):
    if request.method == 'GET':
        distribs = distributions.get_all(
            {'distribution_date__gte': (datetime.date.today() - datetime.timedelta(days=31)).strftime('%Y-%m-%d')})
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

        party_members = Person.objects.filter(party_member=True).order_by('-last_name').all()
        sympathizers = Sympathizer.objects.all()
        newspapers = NewspaperNumber.objects.select_related('newspaper').order_by('year').all()
        return render(request, 'press/new-distrib.html', {
            'form': form,
            'party_members': party_members,
            'sympathizers': sympathizers,
            'newspapers': newspapers,
            'datenow': datetime.date.today()
        })
    elif request.method == 'POST':
        form = DistributionForm(request.POST)
        party_members = request.POST.getlist('party_members', [])
        sympathizers = request.POST.getlist('sympathizer-members', [])
        newspapers = request.POST.getlist('newspaper', [])
        newspapers_quantity = request.POST.getlist('newspaper-quantity', [])

        if len(party_members) + len(sympathizers) == 0:
            form.add_error(None, 'Должен быть хотя бы один раздающий!')

        if len(newspapers) == 0 or len(newspapers_quantity) == 0:
            form.add_error(None, 'Должна быть роздана хотя бы 1 газета')

        if len(newspapers) != len(newspapers_quantity):
            form.add_error(None, 'Некорректно введены данные о газетах!')

        if form.is_valid():
            n_distrib = form.save(commit=False)
            n_distrib.autor_id = request.user.pk
            n_distrib.save()

            for newspaper in zip(newspapers, newspapers_quantity):
                n_newspaper = NewspaperNumbersOnDistribution(
                    number_id=newspaper[0],
                    distribution=n_distrib,
                    quantity=newspaper[1]
                )
                n_newspaper.save()

            for p_member in party_members:
                n_party_member = DistributionPartyMembers(
                    distribution=n_distrib,
                    member_id=p_member
                )
                n_party_member.save()

            sympathizers_ids = [x for x in Sympathizer.objects.all() if
                                x.normalize_name in [name_normalizer(x) for x in sympathizers]]

            for new_sympathizer_name in [x for x in sympathizers if name_normalizer(x) not in [x.normalize_name for x in sympathizers_ids]]:
                n_sympathizer = Sympathizer(name=new_sympathizer_name)
                n_sympathizer.save()
                sympathizers_ids.append(n_sympathizer)

            for sympathizer in sympathizers_ids:
                DistributionSympathizerMember(
                    distribution=n_distrib,
                    member=sympathizer
                ).save()

            return redirect('press:all')

        else:
            print(form.errors)


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


@login_required()
def hx_distrib(request: HttpRequest, pk: int):
    distrib = get_object_or_404(Distribution, pk=pk)
    distrib.delete()
    distribs = distributions.get_all(
        {'distribution_date__gte': (datetime.date.today() - datetime.timedelta(days=31)).strftime('%Y-%m-%d')})
    result = render_block_to_string('press/all_distribution.html', 'table-distrib', {'distribs': distribs}, request)
    return HttpResponse(result)


@login_required()
def report_generate(request: HttpRequest):
    file_report = report.generate_report()
    return FileResponse(file_report, filename='Отчёт о раздачах.xlsx', as_attachment=False)

