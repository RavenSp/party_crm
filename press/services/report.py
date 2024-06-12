import datetime
from press.models import Distribution, NewspaperNumbersOnDistribution
from django.db.models import Count

from django.core.serializers import serialize


def generate_report():
    report_month = _report_month()

    all_distribs = Distribution.objects.filter(
        distribution_date__gte=report_month.replace(month=1, day=1)
    ).filter(
        distribution_date__lt=(report_month.replace(month=report_month.month+1) if report_month.month > 12 else report_month.replace(year=report_month.year +1, month=1, day=1))
    ).all().select_related()

    print(all_distribs.query)

    return serialize('json', all_distribs)
    

def _report_month() -> datetime.date:
    if datetime.date.today().day < 4:
        if datetime.date.today().month == 1:
            report_month = datetime.date.today().replace(month=12).replace(day=1)
        else:
            report_month = datetime.date.today().replace(month=datetime.date.today().month - 1).replace(day=1)
    else:
        report_month = datetime.date.today().replace(day=1)

    return report_month
