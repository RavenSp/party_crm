import datetime
from press.models import Distribution, NewspaperNumbersOnDistribution
from django.db.models import Count
import xlsxwriter
from io import BytesIO
from itertools import chain

from django.core.serializers import serialize


def generate_report():
    report_month = _report_month()

    all_distribs = Distribution.objects.filter(
        distribution_date__gte=report_month.replace(month=1, day=1)
    ).filter(
        distribution_date__lt=(report_month.replace(month=report_month.month+1) if report_month.month < 12 else report_month.replace(year=report_month.year +1, month=1, day=1))
    ).all()


    # print(all_distribs.query)

    bytesFile = BytesIO()

    xls_file = xlsxwriter.Workbook(bytesFile, {'in_memory': True})
    title_style = xls_file.add_format({
        'bold': 1,
        'align': 'center',
        'valign': 'vcenter',
        'font_size': 16,
        'font_name': 'Arial',
        'border': 1
    })

    head_style = xls_file.add_format({
        'bold': 1,
        'align': 'center',
        'valign': 'vcenter',
        'font_size': 14,
        'font_name': 'Arial',
        'border': 1
    })

    simple_style = xls_file.add_format({
        'align': 'center',
        'valign': 'vcenter',
        'font_size': 11,
        'font_name': 'Arial',
        'border': 1
    })
    xls_file.set_properties({
        'title': 'Отчёт о раздачах газет Московской организации РПР',
        'subject': 'Отчёт от раздаче',
        'author': 'Report Maker',
        'created': datetime.date.today(),
    })
    ws1 = xls_file.add_worksheet('Общие данные')
    
    ws1.set_column('A:A', 15)
    ws1.set_column('B:B', 37.4)
    ws1.set_column('C:C', 33.3)
    ws1.set_column('D:D', 17.2)
    ws1.set_column('E:E', 35)
    ws1.merge_range('A1:E1', f"Распространение прессы Московская организация {datetime.date.today().year} год.", title_style)
    ws1.set_row(0, 20)
    ws1.set_row(1, 20)
    for index, cell in enumerate(['Дата', 'Предприятие', 'Газета', 'Количество', 'Распространяли']):
        ws1.write(1, index, cell, head_style)
    for index, distrib in enumerate(all_distribs):
        current_line = index+2
        ws1.write_string(current_line, 0, distrib.distribution_date.strftime("%d.%m.%Y"), simple_style)
        ws1.write_string(current_line, 1, distrib.factory.title, simple_style)
        if distrib.numbers.count() > 1:
            nmbs = distrib.numbers.all()
            ws1.write_string(current_line, 2,
                             ', '.join([f"{x.number.newspaper.short_title} №{x.number.number}" for x in nmbs]), simple_style)
            ws1.write_number(current_line, 3, sum([nmb.quantity for nmb in nmbs]), simple_style)
        else:
            nmb = distrib.numbers.all()[0]
            ws1.write_string(current_line, 2, 
                             f"{nmb.number.newspaper.title} №{nmb.number.number}", simple_style)
            ws1.write_number(current_line, 3, nmb.quantity, simple_style)
        ws1.write_string(current_line, 4, ', '.join(
            chain([x.member.full_name for x in distrib.party_members.all()], 
                  [f'соч. {x.member.name}' for x in distrib.sympathizer_members.all()])
            ), simple_style)
    ws1.write_string(current_line+1, 2, "Итого:", head_style)
    # ws1.write_string(current_line + 1, 3, str(sum([sum([i['quantity'] for i in x.numbers.all().values()]) for x in all_distribs])), head_style)
    ws1.write_formula(current_line + 1, 3, f'=SUM(D3:D{current_line+1})', head_style, '')

    ws2 = xls_file.add_worksheet('Распространители')
    ws2.set_column('A:A', 28.05)
    ws2.set_column('B:N', 13.35)
    ws2.merge_range('A1:N1', f'Распространители Московская организация {datetime.date.today().year} год.', title_style)
    ws2.set_row(0, 20)
    ws2.set_row(1, 20)
    row_text = ['Фамилия', 'Январь', 'Февраль', 'Март', 'Апрель',
                'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь',
                'Октябрь', 'Ноябрь', 'Декабрь', 'Итого:']
    for index, cell in enumerate(row_text):
        ws2.write(1, index, cell, head_style)


    ws3 = xls_file.add_worksheet('Предприятия')
    ws3.set_column('A:A', 40)
    ws3.set_column('B:B', 30)
    ws3.set_column('C:O', 13.35)
    ws3.merge_range('A1:O1', f'Предприятия Московская организация {datetime.date.today().year} год.', title_style)
    ws3.set_row(0, 20)
    ws3.set_row(1, 20)
    row_text = ['Предприятие', 'Город/Населённый пункт', 'Январь', 'Февраль', 'Март', 'Апрель',
                'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь',
                'Октябрь', 'Ноябрь', 'Декабрь', 'Итого:']
    for index, cell in enumerate(row_text):
        ws3.write(1, index, cell, head_style)

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
