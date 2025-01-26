import datetime
from press.models import Distribution, Sympathizer, FactoryPoint
from person.models import Person

import xlsxwriter
from io import BytesIO
from itertools import chain


def generate_report(report_month: datetime.date = None):
    if report_month is None:
        report_month = _report_month()

    all_distribs = Distribution.objects.filter(
        distribution_date__gte=report_month.replace(month=1, day=1)
    ).filter(
        distribution_date__lt=(
            report_month.replace(month=report_month.month + 1) if report_month.month < 12 else report_month.replace(
                year=report_month.year + 1, month=1, day=1))
    ).order_by('distribution_date').all()

    all_party_member = Person.objects.filter(party_member=True).filter(is_active=True).order_by('last_name').all()
    all_sympathizers = Sympathizer.objects.all()

    all_members = ([{'name': x.full_name, 'months': {y: 0 for y in range(1, 13)}} for x in all_party_member] +
                   [{'name': f'соч. {x.name}', 'months': {y: 0 for y in range(1, 13)}} for x in all_sympathizers])

    all_fabric = FactoryPoint.objects.order_by('-town__title', '-title').all()
    factory_month = {x.pk: {y: 0 for y in range(1, 13)} for x in all_fabric}

    for distrib in all_distribs:
        count = sum([x.quantity for x in distrib.numbers.all()])

        ## NEW REALISATION ##

        for party in distrib.party_members.all():
            for mbm in all_members:
                if mbm['name'] == party.member.full_name:
                    mbm['months'][distrib.distribution_date.month] += party.quantity
        for sympathier in distrib.sympathizer_members.all():
            for mbm in all_members:
                if mbm['name'] == f'соч. {sympathier.member.name}':
                    mbm['months'][distrib.distribution_date.month] += sympathier.quantity

        ## OLD REALISATION ##

        # party_member_count = sum([1 for x in distrib.party_members.all()])
        # sympathier_count = sum([1 for x in distrib.sympathizer_members.all()])
        # m_count = party_member_count + sympathier_count
        # for party in distrib.party_members.all():
        #     for mbm in all_members:
        #         if mbm['name'] == party.member.full_name:
        #             mbm['months'][distrib.distribution_date.month] += count // m_count
        # for sympathier in distrib.sympathizer_members.all():
        #     for mbm in all_members:
        #         if mbm['name'] == f'соч. {sympathier.member.name}':
        #             mbm['months'][distrib.distribution_date.month] += count // m_count
        # if count % m_count > 0:
        #     cnt = 0
        #     if sympathier_count > 0:
        #         while cnt < count % m_count:
        #             for mbm in distrib.sympathizer_members.all():
        #                 next(filter(lambda x: x['name'] == f'соч. {mbm.member.name}', all_members))['months'][
        #                     distrib.distribution_date.month] += 1
        #                 cnt += 1
        #                 if cnt == count % m_count:
        #                     break
        #     else:
        #         while cnt < count % m_count:
        #             for mbm in distrib.party_members.all():
        #                 next(filter(lambda x: x['name'] == mbm.member.full_name, all_members))['months'][
        #                     distrib.distribution_date.month] += 1
        #                 cnt += 1
        #                 if cnt == count % m_count:
        #                     break

        factory_month[distrib.factory.id][distrib.distribution_date.month] += count

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
    ws1.set_column('E:E', 72)
    ws1.merge_range('A1:E1', f"Распространение прессы Московская организация {datetime.date.today().year} год.", title_style)
    ws1.set_row(0, 20)
    ws1.set_row(1, 20)
    for index, cell in enumerate(['Дата', 'Предприятие', 'Газета', 'Количество', 'Распространяли']):
        ws1.write(1, index, cell, head_style)
    current_line = 0
    for index, distrib in enumerate(all_distribs):
        current_line = index + 2
        ws1.write_string(current_line, 0, distrib.distribution_date.strftime("%d.%m.%Y"), simple_style)
        ws1.write_string(current_line, 1, distrib.factory.title, simple_style)
        if distrib.numbers.count() > 1:
            nmbs = distrib.numbers.all()
            ws1.write_string(current_line, 2,
                             ', '.join([f"{x.number.newspaper.short_title} №{x.number.number}" for x in nmbs]),
                             simple_style)
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
    ws1.write_string(current_line + 1, 2, "Итого:", head_style)
    # ws1.write_string(current_line + 1, 3, str(sum([sum([i['quantity'] for i in x.numbers.all().values()]) for x in all_distribs])), head_style)
    ws1.write_formula(current_line + 1, 3, f'=SUM(D3:D{current_line + 1})', head_style, '')

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
    for index, mbm in enumerate(all_members):
        current_line = index + 2
        ws2.write_string(current_line, 0, mbm['name'], simple_style)
        for i in mbm['months']:
            if mbm['months'][i] > 0:
                ws2.write_number(current_line, i, mbm['months'][i], simple_style)
            else:
                ws2.write_string(current_line, i, '', simple_style)
        ws2.write_formula(current_line, 13, f'=SUM(B{current_line + 1}:M{current_line + 1})', head_style, '')
    ws2.write_string(current_line + 1, 0, 'ИТОГО:', head_style)
    for index, i in enumerate('BCDEFGHIJKLMN'):
        ws2.write_formula(current_line + 1, index + 1, f'SUM({i}3:{i}{current_line + 1})', head_style, '')

    ws3 = xls_file.add_worksheet('Предприятия')
    ws3.set_column('A:A', 40)
    ws3.set_column('B:B', 30)
    ws3.set_column('C:O', 13.35)
    ws3.merge_range('A1:O1', f'Предприятия Московская организация {datetime.date.today().year} год.', title_style)
    ws3.set_row(0, 20)
    ws3.set_row(1, 20)
    row_text = ['Предприятие', 'Город', 'Январь', 'Февраль', 'Март', 'Апрель',
                'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь',
                'Октябрь', 'Ноябрь', 'Декабрь', 'Итого:']
    for index, cell in enumerate(row_text):
        ws3.write(1, index, cell, head_style)

    for index, fab in enumerate(all_fabric):
        current_line = index + 2
        ws3.write_string(current_line, 0, fab.title, simple_style)
        ws3.write_string(current_line, 1, fab.town.title, simple_style)
        for ind, i in enumerate('CDEFGHIJKLMN'):
            if factory_month[fab.id][ind + 1] > 0:
                ws3.write_number(current_line, ind + 2, factory_month[fab.id][ind + 1], simple_style)
            else:
                ws3.write_string(current_line, ind + 2, '', simple_style)
        ws3.write_formula(current_line, 14, f'=SUM(C{current_line + 1}:N{current_line + 1})', head_style, '')
    ws3.write_string(current_line + 1, 1, 'Итого', head_style)

    for ind, i in enumerate('CDEFGHIJKLMNO'):
        ws3.write_formula(current_line + 1, ind + 2, f'=SUM({i}3:{i}{current_line + 1})', head_style, '')
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
