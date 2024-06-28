import datetime
from django_htmx.http import retarget
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse, FileResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .forms import DistributionForm, FabricForm, NewspapersNumberForm
from .models import FactoryPoint, Sympathizer, NewspaperNumber, NewspaperNumbersOnDistribution, \
    DistributionPartyMembers, DistributionSympathizerMember, Distribution, Town, Newspaper
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
    if request.method == 'POST':
        filters = request.POST.dict()
        distribs = distributions.get_all({x: filters[x] for x in filters if filters[x] != ''})
        result = render_block_to_string('press/all_distribution.html', 'table-distrib', {'distribs': distribs}, request)
        return HttpResponse(result, status='200')


@login_required()
def new_distrib(request: HttpRequest):
    if request.method == 'GET':
        form = DistributionForm(initial={
            'distribution_date': datetime.date.today().strftime('%Y-%m-%d'),
            'start_time': (datetime.datetime.now() - datetime.timedelta(minutes=60)).strftime("%H:%M"),
            'end_time': datetime.datetime.now().strftime("%H:%M"),
        })
        factoryes = FactoryPoint.objects.select_related('town').order_by('-town__title', 'title').all()
        party_members = Person.objects.filter(party_member=True).order_by('-last_name').all()
        sympathizers = Sympathizer.objects.all()
        newspapers = NewspaperNumber.objects.select_related('newspaper').order_by('year').all()
        return render(request, 'press/new-distrib.html', {
            'form': form,
            'party_members': party_members,
            'sympathizers': sympathizers,
            'newspapers': newspapers,
            'factoryes': factoryes,
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

            sympathizers_ids = [x for x in Sympathizer.objects.all() if
                                x.normalize_name in [name_normalizer(x) for x in sympathizers]]

            for new_sympathizer_name in [x for x in sympathizers if
                                         name_normalizer(x) not in [x.normalize_name for x in sympathizers_ids]]:
                n_sympathizer = Sympathizer(name=new_sympathizer_name)
                n_sympathizer.save()
                sympathizers_ids.append(n_sympathizer)

            all_memb_count = len(party_members) + len(sympathizers)
            all_quantity = sum([int(x) for x in newspapers_quantity])
            cnt_memb = {x: all_quantity // all_memb_count for x in party_members}
            cnt_symp = {x.pk: all_quantity // all_memb_count for x in sympathizers_ids}

            if all_quantity % all_memb_count and len(sympathizers) > 0:
                for i in cnt_symp:
                    cnt_symp[i] += (all_quantity % all_memb_count) // len(sympathizers)
                if (all_quantity % all_memb_count) % len(sympathizers):
                    for i in [x for x in cnt_symp][:(all_quantity % all_memb_count) % len(sympathizers)]:
                        cnt_symp[i] += 1
            elif all_quantity % all_memb_count:
                for i in cnt_memb:
                    cnt_memb[i] += (all_quantity % all_memb_count) // len(party_members)
                if (all_quantity % all_memb_count) % len(party_members):
                    for i in [x for x in cnt_memb][:(all_quantity % all_memb_count) % len(party_members)]:
                        cnt_memb[i] += 1

            for sympathizer in sympathizers_ids:
                print(sympathizer)
                DistributionSympathizerMember(
                    distribution=n_distrib,
                    member=sympathizer,
                    quantity=cnt_symp.get(sympathizer.pk, 0)
                ).save()

            for p_member in party_members:
                n_party_member = DistributionPartyMembers(
                    distribution=n_distrib,
                    member_id=p_member,
                    quantity=cnt_memb.get(p_member, 0)
                )
                n_party_member.save()

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


@login_required()
def towns(request: HttpRequest):
    if request.method == 'GET':
        towns = Town.objects.prefetch_related('factories').order_by('title').all()
        return render(request, 'press/towns.html', {'towns': towns})
    if request.method == 'POST':
        town_name = request.POST.get('town-name', None)
        if town_name is None or town_name == '':
            return retarget(render(request, 'error_alert.html', {'alert_message': 'Имя не должно быть пустым!'}),
                            '#modal-alert')
        if Town.objects.filter(title=town_name).exists():
            return retarget(render(request, 'error_alert.html', {'alert_message': 'Имя должно быть уникальным!'}),
                            '#modal-alert')
        town = Town(title=town_name)
        town.save()
        towns = Town.objects.prefetch_related('factories').order_by('title').all()
        html = render_block_to_string('press/towns.html', 'towns_list', {'towns': towns}, request)

        return HttpResponse(html, status='201')


@login_required()
def towns_delete(request: HttpRequest, pk: int):
    if request.method == 'DELETE':
        town = Town.objects.get(pk=pk)
        town.delete()
        return HttpResponse(request, '', status='200')


@login_required()
def factory(request: HttpRequest):
    if request.method == 'GET':
        fabrics = FactoryPoint.objects.prefetch_related('town').prefetch_related('distributions').order_by(
            'town__title', 'title').all()
        form = FabricForm()
        return render(request, 'press/factory-point.html', {'fabrics': fabrics, 'form': form})
    if request.method == 'POST':
        fabric_form = FabricForm(request.POST)
        if fabric_form.is_valid():
            fabric_form.save()
        else:
            error_list = "\n".join([x for x in list(fabric_form.errors.values())])
            return retarget(
                render(request, 'error_alert.html', {'alert_message': f'Исправьте следующие ошибки: {error_list}'}),
                '#modal-alert')
        fabrics = FactoryPoint.objects.prefetch_related('town').prefetch_related('distributions').order_by(
            'town__title', 'title').all()
        html = render_block_to_string('press/factory-point.html', 'factory_list', {'fabrics': fabrics}, request)
        return HttpResponse(html, status='201')

    if request.method == 'DELETE':
        fabric_id = request.GET.get('id', None)
        if fabric_id is None:
            return HttpResponse('', status='404')
        fabric = FactoryPoint.objects.get(pk=fabric_id)
        if fabric is None:
            return HttpResponse('', status='404')
        fabric.delete()
        return HttpResponse(request, '', status='200')


@login_required()
def newspaper(request: HttpRequest):
    if request.method == 'GET':
        newspapers = Newspaper.objects.order_by('title').all()
        return render(request, 'press/newspapers.html', {'newspapers': newspapers})

    if request.method == 'POST':
        title = request.POST.get('title', '')
        short_title = request.POST.get('short-title', '')
        if title.strip == '':
            return retarget(
                render(request, 'error_alert.html', {'alert_message': f'Поле Название не должно быть пустым!'}),
                '#modal-alert')
        if short_title.strip == '':
            return retarget(
                render(request, 'error_alert.html', {'alert_message': f'Поле Краткое название не должно быть пустым!'}),
                '#modal-alert')
        newspaper_new = Newspaper(title=title, short_title=short_title)
        newspaper_new.save()
        newspapers = Newspaper.objects.order_by('title').all()
        html = render_block_to_string('press/newspapers.html', 'newspaper_list', {'newspapers': newspapers}, request)
        return HttpResponse(html, status='201')

    if request.method == 'DELETE':
        newspaper_id = request.GET.get('id', None)
        if newspaper_id is None:
            return HttpResponse('', status='404')
        newspaper_d = Newspaper.objects.get(pk=newspaper_id)
        if newspaper_d is None:
            return HttpResponse('', status='404')
        newspaper_d.delete()
        return HttpResponse(request, '', status='200')


@login_required()
def newspaper_numbers(request: HttpRequest):
    if request.method == 'GET':
        newspapers_numbers = NewspaperNumber.objects.select_related('newspaper').order_by('newspaper__title',
                                                                                          '-year').all()
        form = NewspapersNumberForm()
        return render(request, 'press/newspaper-numbers.html', {'newspapers_numbers': newspapers_numbers, 'form': form})

    if request.method == 'DELETE':
        newspaper_number_id = request.GET.get('id', None)
        if newspaper_number_id is None:
            return HttpResponse('', status='404')
        newspaper_d = NewspaperNumber.objects.get(pk=newspaper_number_id)
        if newspaper_d is None:
            return HttpResponse('', status='404')
        newspaper_d.delete()
        return HttpResponse(request, '', status='200')

    if request.method == 'POST':
        updated_request = request.POST.copy()
        updated_request.update({'year': updated_request.get('year', '') + '-01'})

        form = NewspapersNumberForm(updated_request)

        if form.is_valid():
            form.save()
        else:
            print(form.errors)
            return retarget(
                render(request, 'error_alert.html', {'alert_message': f'Исправьте следующие ошибки'}),
                '#modal-alert')
        newspapers_numbers = NewspaperNumber.objects.select_related('newspaper').order_by('newspaper__title',
                                                                                          'year').all()
        html = render_block_to_string('press/newspaper-numbers.html', 'numbers_list',
                                      {'newspapers_numbers': newspapers_numbers}, request)
        return HttpResponse(html, status='201')
