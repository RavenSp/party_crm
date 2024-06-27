from django.shortcuts import render
from django.http import HttpRequest
from person.services.login import auth_user
from press.models import DistributionPartyMembers, Distribution
import datetime
# Create your views here.


def login(request: HttpRequest):
    if request.method == 'POST':
        return auth_user(request, email=request.POST.get('email', None),
                                       password=request.POST.get('password', None))
    return render(request, 'login.html', {})


def profile(request: HttpRequest):
    my_distribution = DistributionPartyMembers.objects.select_related('distribution')\
        .filter(member_id=request.user.pk)\
        .filter(distribution__distribution_date__month=datetime.date.today().month)\
        .filter(distribution__distribution_date__year=datetime.date.today().year)\
        .all()
    all_distribution = DistributionPartyMembers.objects.select_related('distribution')\
        .filter(member_id=request.user.pk)\
        .all()

    return render(request, 'person/profile.html',
                  {'my_distribution': my_distribution,
                   'all_distribution': all_distribution})
