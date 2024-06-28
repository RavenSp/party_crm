from django.db.models import Sum
from django.shortcuts import render, redirect
from django.http import HttpRequest
from person.services.login import auth_user
from press.models import DistributionPartyMembers, Distribution
import datetime
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required


# Create your views here.


def login(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect(to='/profile/')
    if request.method == 'POST':
        return auth_user(request, email=request.POST.get('email', None),
                         password=request.POST.get('password', None))
    return render(request, 'login.html', {})


@login_required()
def profile(request: HttpRequest):
    my_distribution = DistributionPartyMembers.objects.select_related('distribution') \
        .filter(member_id=request.user.pk) \
        .filter(distribution__distribution_date__month=datetime.date.today().month) \
        .filter(distribution__distribution_date__year=datetime.date.today().year) \
        .order_by('distribution__distribution_date')\
        .all()
    all_distribution = DistributionPartyMembers.objects.select_related('distribution') \
        .filter(member_id=request.user.pk) \
        .order_by('distribution__distribution_date') \
        .all()

    sum_my_distrib = sum([x.quantity for x in my_distribution if x.quantity])
    sum_all_distrib = sum([x.quantity for x in all_distribution if x.quantity])

    return render(request, 'person/profile.html',
                  {'my_distribution': my_distribution,
                   'all_distribution': all_distribution,
                   'sum_my_distrib': sum_my_distrib,
                   'sum_all_distrib': sum_all_distrib})


def logout_view(request):
    logout(request)
    return redirect('login')
