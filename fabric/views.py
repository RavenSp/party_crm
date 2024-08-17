from django.shortcuts import render
from render_block import render_block_to_string
from django.contrib.auth.decorators import login_required
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django_htmx.http import retarget
from fabric.forms import FabricForm
from fabric.models import FactoryPoint, Town



@login_required()
def factory(request: HttpRequest):
    if request.method == 'GET':
        fabrics = FactoryPoint.objects.prefetch_related('town').prefetch_related('distributions').order_by(
            'town__title', 'title').all()
        form = FabricForm()
        return render(request, 'fabric/factory-point.html', {'fabrics': fabrics, 'form': form})
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
        html = render_block_to_string('fabric/factory-point.html', 'factory_list', {'fabrics': fabrics}, request)
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
def towns(request: HttpRequest):
    if request.method == 'GET':
        towns = Town.objects.prefetch_related('factories').order_by('title').all()
        return render(request, 'fabric/towns.html', {'towns': towns})
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
        html = render_block_to_string('fabric/towns.html', 'towns_list', {'towns': towns}, request)

        return HttpResponse(html, status='201')

#TODO: Слить с предыдущим методом
@login_required()
def towns_delete(request: HttpRequest, pk: int):
    if request.method == 'DELETE':
        town = Town.objects.get(pk=pk)
        town.delete()
        return HttpResponse(request, '', status='200')
