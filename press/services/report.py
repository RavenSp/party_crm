import datetime
from press.models import Distribution, NewspaperNumbersOnDistribution
from django.db.models import Count
import xlsxwriter
from io import BytesIO

from django.core.serializers import serialize


def generate_report():
    report_month = _report_month()

    all_distribs = Distribution.objects.filter(
        distribution_date__gte=report_month.replace(month=1, day=1)
    ).filter(
        distribution_date__lt=(report_month.replace(month=report_month.month+1) if report_month.month > 12 else report_month.replace(year=report_month.year +1, month=1, day=1))
    ).prefetch_related('numbers')\
    .prefetch_related('newspaper_numbers').all()

    print(all_distribs.query)

    bytesFile = BytesIO()

    xls_file = xlsxwriter.Workbook(bytesFile, {'in_memory': True})
    title_style = xls_file.add_format({
        'bold': 1,
        'align': 'center',
        'valign': 'vcenter',
        'font_size': 16
    })
    ws1 = xls_file.add_worksheet('Общие данные')
    ws1.set_column('A:A', 15)
    ws1.set_column('B:B', 37.4)
    ws1.set_column('C:C', 33.3)
    ws1.set_column('D:D', 17.2)
    ws1.set_column('E:E', 35)
    ws1.merge_range('A1:E1', f"Распространение прессы Московская организация {datetime.date.today().year} год.", title_style)

    ws2 = xls_file.add_worksheet('Распространители')
    ws2.merge_range('A1:O1', f'Распространители Московская организация {datetime.date.today().year} год.', title_style)
    ws3 = xls_file.add_worksheet('Предприятия')
    ws3.merge_range('A1:O1', f'Предприятия Московская организация {datetime.date.today().year} год.', title_style)


    xls_file.close()
    bytesFile.seek(0)

    return bytesFile

def _report_month() -> datetime.date:
    if datetime.date.today().day < 4:
        if datetime.date.today().month == 1:
            report_month = datetime.date.today().replace(month=12).replace(day=1)
        else:
            report_month = datetime.date.today().replace(month=datetime.date.today().month - 1).replace(day=1)
    else:
        report_month = datetime.date.today().replace(day=1)

    return report_month
