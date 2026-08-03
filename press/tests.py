import datetime
import zipfile
from io import BytesIO
from unittest import mock

from django.core import mail
from django.core.management.base import CommandError
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from press.forms import DistributionForm, FabricForm, NewspapersNumberForm
from press.models import (
    Distribution,
    DistributionPartyMembers,
    DistributionSympathizerMember,
    FactoryPoint,
    Newspaper,
    NewspaperNumber,
    NewspaperNumbersOnDistribution,
    Sympathizer,
    Town,
)
from press.services import distributions, factory, mail as mail_service, newspaper, report
from django.contrib.auth import get_user_model


def _get_user_model():
    return get_user_model()


class PressBaseTestCase(TestCase):
    """Базовый класс с фикстурами для тестов приложения press."""

    @classmethod
    def setUpTestData(cls):
        cls.user = _get_user_model().objects.create_user(
            email='user@example.com',
            password='pass1234',
            last_name='Иванов',
            first_name='Иван',
        )
        cls.party_member = _get_user_model().objects.create_user(
            email='party@example.com',
            password='pass1234',
            last_name='Петров',
            first_name='Пётр',
            party_member=True,
        )
        cls.sympathizer = Sympathizer.objects.create(name='Сидоров Алексей')
        cls.town = Town.objects.create(title='Москва')
        cls.factory = FactoryPoint.objects.create(title='Завод имени Ленина', town=cls.town)
        cls.newspaper = Newspaper.objects.create(title='Правда', short_title='Пр')
        cls.number = NewspaperNumber.objects.create(
            newspaper=cls.newspaper,
            number='1',
            year=datetime.date(2024, 1, 1),
        )

    def setUp(self):
        self.client = Client()
        self.client.login(email='user@example.com', password='pass1234')


class ModelsTests(PressBaseTestCase):
    """Тесты моделей приложения press."""

    def test_newspaper_str(self):
        self.assertEqual(str(self.newspaper), 'Правда')

    def test_newspaper_number_str(self):
        self.assertEqual(str(self.number), 'Правда 1')

    def test_newspaper_number_related_name(self):
        # related_name текущей реализации — 'newspaper'
        self.assertEqual(list(self.newspaper.newspaper.all()), [self.number])

    def test_sympathizer_str(self):
        self.assertEqual(str(self.sympathizer), 'соч. Сидоров Алексей')

    def test_sympathizer_normalize_name(self):
        self.assertEqual(self.sympathizer.normalize_name, 'сидоровалексей')

    def test_town_str(self):
        self.assertEqual(str(self.town), 'Москва')

    def test_factory_str(self):
        self.assertEqual(str(self.factory), 'Завод имени Ленина')

    def test_factory_related_name(self):
        self.assertEqual(list(self.town.factories.all()), [self.factory])

    def test_distribution_str(self):
        distribution = Distribution.objects.create(
            distribution_date=datetime.date(2024, 1, 15),
            autor=self.user,
            factory=self.factory,
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
        )
        self.assertEqual(str(distribution), 'Раздача 15.01.2024 на Завод имени Ленина')

    def test_distribution_count_members_current_behavior(self):
        """
        count_members использует len() на RelatedManager.
        Это известная проблема; тест фиксирует текущее поведение.
        """
        distribution = Distribution.objects.create(
            distribution_date=datetime.date(2024, 1, 15),
            autor=self.user,
            factory=self.factory,
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
        )
        with self.assertRaises(TypeError):
            distribution.count_members()

    def test_distribution_count_members_prefetch_still_raises(self):
        """
        prefetch_related не превращает RelatedManager в список,
        поэтому count_members продолжает падать с TypeError.
        """
        distribution = Distribution.objects.create(
            distribution_date=datetime.date(2024, 1, 15),
            autor=self.user,
            factory=self.factory,
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
        )
        DistributionPartyMembers.objects.create(
            distribution=distribution, member=self.party_member, quantity=10
        )
        DistributionSympathizerMember.objects.create(
            distribution=distribution, member=self.sympathizer, quantity=5
        )
        distribution = Distribution.objects.prefetch_related(
            'party_members', 'sympathizer_members'
        ).get(pk=distribution.pk)
        with self.assertRaises(TypeError):
            distribution.count_members()

    def test_newspaper_numbers_on_distribution_str(self):
        distribution = Distribution.objects.create(
            distribution_date=datetime.date(2024, 1, 15),
            autor=self.user,
            factory=self.factory,
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
        )
        line = NewspaperNumbersOnDistribution.objects.create(
            distribution=distribution, number=self.number, quantity=10
        )
        self.assertTrue(str(line).startswith('Номер в раздаче ID'))

    def test_distribution_party_members_str(self):
        distribution = Distribution.objects.create(
            distribution_date=datetime.date(2024, 1, 15),
            autor=self.user,
            factory=self.factory,
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
        )
        line = DistributionPartyMembers.objects.create(
            distribution=distribution, member=self.party_member, quantity=10
        )
        self.assertTrue(str(line).startswith('Член партии на раздаче ID'))

    def test_distribution_sympathizer_member_str(self):
        distribution = Distribution.objects.create(
            distribution_date=datetime.date(2024, 1, 15),
            autor=self.user,
            factory=self.factory,
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
        )
        line = DistributionSympathizerMember.objects.create(
            distribution=distribution, member=self.sympathizer, quantity=5
        )
        self.assertTrue(str(line).startswith('Сочувствующий на раздаче ID'))


class FormsTests(PressBaseTestCase):
    """Тесты форм приложения press."""

    def test_distribution_form_valid(self):
        form = DistributionForm(data={
            'distribution_date': '2024-01-15',
            'factory': self.factory.pk,
            'start_time': '10:00',
            'end_time': '12:00',
            'description': 'Тестовая раздача',
        })
        self.assertTrue(form.is_valid())

    def test_distribution_form_invalid_missing_factory(self):
        form = DistributionForm(data={
            'distribution_date': '2024-01-15',
            'start_time': '10:00',
            'end_time': '12:00',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('factory', form.errors)

    def test_fabric_form_valid(self):
        form = FabricForm(data={
            'town': self.town.pk,
            'title': 'Новый завод',
            'description': 'Описание',
        })
        self.assertTrue(form.is_valid())

    def test_newspapers_number_form_valid(self):
        form = NewspapersNumberForm(data={
            'newspaper': self.newspaper.pk,
            'number': '42',
            'year': '2024-01-01',
        })
        self.assertTrue(form.is_valid())


class ServicesTests(PressBaseTestCase):
    """Тесты сервисного слоя приложения press."""

    def test_distributions_get_all_by_date(self):
        Distribution.objects.create(
            distribution_date=datetime.date(2024, 1, 15),
            autor=self.user,
            factory=self.factory,
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
        )
        result = distributions.get_all({'distribution_date': '2024-01-15'})
        self.assertEqual(len(result), 1)

    def test_distributions_get_all_empty(self):
        result = distributions.get_all({'distribution_date': '2099-01-01'})
        self.assertEqual(result, [])

    def test_factory_get_all(self):
        result = factory.get_all({'town': self.town.pk})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, 'Завод имени Ленина')

    def test_factory_get_all_empty(self):
        other_town = Town.objects.create(title='Другой город')
        result = factory.get_all({'town': other_town.pk})
        self.assertEqual(result, [])

    def test_newspaper_add(self):
        pk = newspaper.add_newspaper(title='Новая газета', short_title='НГ')
        created = Newspaper.objects.get(pk=pk)
        self.assertEqual(created.title, 'Новая газета')
        self.assertEqual(created.short_title, 'НГ')

    def test_newspaper_edit(self):
        pk = newspaper.add_newspaper(title='Старая газета', short_title='СГ')
        result = newspaper.edit_newspaper(pk, title='Новое название')
        self.assertEqual(result['title'], 'Новое название')

    def test_newspaper_get_by_id(self):
        result = newspaper.get_newspaper_by_id(self.newspaper.pk)
        self.assertEqual(result['title'], 'Правда')

    def test_newspaper_get_all(self):
        result = newspaper.get_all_newspapers(filter_by={'title': 'Правда'})
        self.assertEqual(len(result), 1)

    def test_newspaper_get_all_without_filter_current_behavior(self):
        """
        Если не передавать filter_by (или передать пустой dict),
        функция возвращает Manager и падает с TypeError.
        Тест фиксирует текущее поведение.
        """
        with self.assertRaises(TypeError):
            newspaper.get_all_newspapers()

    def test_generate_report_returns_bytesio(self):
        report_month = datetime.date(2024, 1, 1)
        result = report.generate_report(report_month=report_month)
        self.assertIsInstance(result, BytesIO)
        self.assertGreater(len(result.read()), 0)

    def test_generate_report_with_distribution(self):
        distribution = Distribution.objects.create(
            distribution_date=datetime.date(2024, 2, 10),
            autor=self.user,
            factory=self.factory,
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
        )
        NewspaperNumbersOnDistribution.objects.create(
            distribution=distribution, number=self.number, quantity=10
        )
        DistributionPartyMembers.objects.create(
            distribution=distribution, member=self.party_member, quantity=10
        )
        result = report.generate_report(report_month=datetime.date(2024, 2, 1))
        self.assertIsInstance(result, BytesIO)

    def test_report_month_default(self):
        today = datetime.date.today()
        result = report._report_month()
        self.assertEqual(result.day, 1)

    def test_send_report(self):
        report_file = BytesIO(b'fake xlsx content')
        mail_service.send_report('test@example.com', 2024, report_file)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Отчёт о раздачах газет за 2024 год', mail.outbox[0].subject)


class ViewsTests(PressBaseTestCase):
    """Тесты view приложения press."""

    def test_my_distribution_get(self):
        response = self.client.get(reverse('press:all'))
        self.assertEqual(response.status_code, 200)

    def test_my_distribution_post_filter(self):
        Distribution.objects.create(
            distribution_date=datetime.date.today(),
            autor=self.user,
            factory=self.factory,
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
        )
        response = self.client.post(reverse('press:all'), {
            'distribution_date': datetime.date.today().strftime('%Y-%m-%d'),
        })
        self.assertEqual(response.status_code, 200)

    def test_new_distrib_get(self):
        response = self.client.get(reverse('press:new-distrib'))
        self.assertEqual(response.status_code, 200)

    def test_new_distrib_post_success(self):
        response = self.client.post(reverse('press:new-distrib'), {
            'distribution_date': '2024-01-15',
            'factory': self.factory.pk,
            'start_time': '10:00',
            'end_time': '12:00',
            'description': 'Раздача',
            'party_members': [self.party_member.pk],
            'newspaper': [self.number.pk],
            'newspaper-quantity': ['10'],
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Distribution.objects.filter(factory=self.factory).exists())

    def test_new_distrib_post_no_members(self):
        """
        Если не указаны раздающие, форма невалидна, но view не возвращает
        HttpResponse. Тест фиксирует текущее поведение.
        """
        with self.assertRaises(ValueError):
            self.client.post(reverse('press:new-distrib'), {
                'distribution_date': '2024-01-15',
                'factory': self.factory.pk,
                'start_time': '10:00',
                'end_time': '12:00',
                'newspaper': [self.number.pk],
                'newspaper-quantity': ['10'],
            })
        self.assertFalse(Distribution.objects.filter(factory=self.factory).exists())

    def test_new_distrib_post_zero_members(self):
        """
        Если списки раздающих пустые, форма невалидна, view не возвращает
        HttpResponse. Тест фиксирует текущее поведение.
        """
        with self.assertRaises(ValueError):
            self.client.post(reverse('press:new-distrib'), {
                'distribution_date': '2024-01-15',
                'factory': self.factory.pk,
                'start_time': '10:00',
                'end_time': '12:00',
                'party_members': [],
                'sympathizer-members': [],
                'newspaper': [self.number.pk],
                'newspaper-quantity': ['10'],
            })

    def test_hx_newspaper(self):
        response = self.client.get(reverse('press:hx-newspaper-field'))
        self.assertEqual(response.status_code, 200)

    def test_hx_distrib_delete(self):
        distribution = Distribution.objects.create(
            distribution_date=datetime.date.today(),
            autor=self.user,
            factory=self.factory,
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
        )
        response = self.client.delete(reverse('press:hx-distrib', kwargs={'pk': distribution.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Distribution.objects.filter(pk=distribution.pk).exists())

    def test_report_generate_get(self):
        response = self.client.get(reverse('press:report-generate'))
        self.assertEqual(response.status_code, 200)

    def test_report_generate_post(self):
        response = self.client.post(reverse('press:report-generate'), {
            'report-year': '2024',
            'report-email': 'boss@example.com',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

    def test_towns_get(self):
        response = self.client.get(reverse('press:towns'))
        self.assertEqual(response.status_code, 200)

    def test_towns_post(self):
        response = self.client.post(reverse('press:towns'), {'town-name': 'Новый город'})
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Town.objects.filter(title='Новый город').exists())

    def test_towns_post_empty_name(self):
        response = self.client.post(reverse('press:towns'), {'town-name': ''})
        self.assertEqual(response.status_code, 200)

    def test_towns_post_duplicate_name(self):
        response = self.client.post(reverse('press:towns'), {'town-name': 'Москва'})
        self.assertEqual(response.status_code, 200)

    def test_towns_delete(self):
        town = Town.objects.create(title='Удаляемый')
        response = self.client.delete(reverse('press:towns-delete', kwargs={'pk': town.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Town.objects.filter(pk=town.pk).exists())

    def test_factory_get(self):
        response = self.client.get(reverse('press:factory'))
        self.assertEqual(response.status_code, 200)

    def test_factory_post(self):
        response = self.client.post(reverse('press:factory'), {
            'town': self.town.pk,
            'title': 'Фабрика',
            'description': 'Описание',
        })
        self.assertEqual(response.status_code, 201)
        self.assertTrue(FactoryPoint.objects.filter(title='Фабрика').exists())

    def test_factory_delete(self):
        factory_point = FactoryPoint.objects.create(title='Удаляемый', town=self.town)
        response = self.client.delete(f"{reverse('press:factory')}?id={factory_point.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(FactoryPoint.objects.filter(pk=factory_point.pk).exists())

    def test_factory_delete_no_id(self):
        response = self.client.delete(reverse('press:factory'))
        self.assertEqual(response.status_code, 404)

    def test_newspaper_get(self):
        response = self.client.get(reverse('press:newspaper'))
        self.assertEqual(response.status_code, 200)

    def test_newspaper_post(self):
        response = self.client.post(reverse('press:newspaper'), {
            'title': 'Известия',
            'short-title': 'Из',
        })
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Newspaper.objects.filter(title='Известия').exists())

    def test_newspaper_post_empty_title_current_behavior(self):
        """
        В view используется title.strip == '' (без вызова метода),
        поэтому пустое название проходит валидацию.
        Тест фиксирует текущее поведение.
        """
        response = self.client.post(reverse('press:newspaper'), {
            'title': '   ',
            'short-title': 'Из',
        })
        self.assertEqual(response.status_code, 201)

    def test_newspaper_delete(self):
        newspaper_obj = Newspaper.objects.create(title='Удаляемая', short_title='Уд')
        response = self.client.delete(f"{reverse('press:newspaper')}?id={newspaper_obj.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Newspaper.objects.filter(pk=newspaper_obj.pk).exists())

    def test_newspaper_numbers_get(self):
        response = self.client.get(reverse('press:newspaper-numbers'))
        self.assertEqual(response.status_code, 200)

    def test_newspaper_numbers_post(self):
        response = self.client.post(reverse('press:newspaper-numbers'), {
            'newspaper': self.newspaper.pk,
            'number': '99',
            'year': '2024-06',
        })
        self.assertEqual(response.status_code, 201)
        self.assertTrue(NewspaperNumber.objects.filter(number='99').exists())

    def test_newspaper_numbers_delete(self):
        number = NewspaperNumber.objects.create(newspaper=self.newspaper, number='Для удаления')
        response = self.client.delete(f"{reverse('press:newspaper-numbers')}?id={number.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(NewspaperNumber.objects.filter(pk=number.pk).exists())

    def test_login_required_redirect(self):
        self.client.logout()
        response = self.client.get(reverse('press:all'))
        self.assertEqual(response.status_code, 302)


class ManagementCommandTests(PressBaseTestCase):
    """Тесты management-команд приложения press."""

    @override_settings(REPORT_MONTH_EMAIL='report@example.com')
    def test_send_report_command(self):
        from io import StringIO
        from press.management.commands.send_report import Command
        out = StringIO()
        command = Command()
        command.stdout = out
        command.handle()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Email с отчётом успешно отправлен', out.getvalue())


class DeprecatedViewsTests(PressBaseTestCase):
    """Тесты deprecated view, сохранённых для обратной совместимости."""

    def test_new_party_member_distrib(self):
        response = self.client.post(reverse('press:htmx-add-party-member'))
        self.assertEqual(response.status_code, 200)

    def test_new_sympathizer_distrib(self):
        response = self.client.post(reverse('press:htmx-add-sympathizer'))
        self.assertEqual(response.status_code, 200)

    def test_hx_add_party_member(self):
        response = self.client.post(reverse('press:hx-add-party-member'), {
            'select-party-members': self.party_member.pk,
        })
        self.assertEqual(response.status_code, 200)

    def test_hx_delete_party_member(self):
        response = self.client.delete(
            reverse('press:hx-delete-pary-member', kwargs={'id_delete_member': self.party_member.pk})
        )
        self.assertEqual(response.status_code, 204)


class ServicesExtraTests(PressBaseTestCase):
    """Дополнительные тесты сервисного слоя press."""

    def _make_distribution(self, date, factory=None):
        return Distribution.objects.create(
            distribution_date=date,
            autor=self.user,
            factory=factory or self.factory,
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
        )

    def test_distributions_get_all_by_factory(self):
        other_town = Town.objects.create(title='Другой город')
        other_factory = FactoryPoint.objects.create(title='Другой завод', town=other_town)
        self._make_distribution(datetime.date(2024, 1, 15))
        self._make_distribution(datetime.date(2024, 1, 15), factory=other_factory)
        result = distributions.get_all({'factory': self.factory.pk})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].factory, self.factory)

    def test_distributions_get_all_ordering(self):
        old = self._make_distribution(datetime.date(2024, 1, 10))
        new = self._make_distribution(datetime.date(2024, 1, 20))
        result = distributions.get_all({'distribution_date__gte': '2024-01-01'})
        self.assertEqual([x.pk for x in result], [new.pk, old.pk])

    def test_newspaper_edit_only_short_title(self):
        result = newspaper.edit_newspaper(self.newspaper.pk, short_title='НП')
        self.assertEqual(result['short_title'], 'НП')
        self.assertEqual(result['title'], 'Правда')

    def test_newspaper_edit_without_params(self):
        """Вызов без параметров не меняет запись."""
        result = newspaper.edit_newspaper(self.newspaper.pk)
        self.assertEqual(result['title'], 'Правда')
        self.assertEqual(result['short_title'], 'Пр')

    def test_newspaper_get_by_id_missing(self):
        with self.assertRaises(Newspaper.DoesNotExist):
            newspaper.get_newspaper_by_id(9999)

    def test_newspaper_edit_missing(self):
        with self.assertRaises(Newspaper.DoesNotExist):
            newspaper.edit_newspaper(9999, title='Нет такой')

    def test_newspaper_get_all_no_matches(self):
        result = newspaper.get_all_newspapers(filter_by={'title': 'Несуществующая'})
        self.assertEqual(result, [])

    def test_send_report_attachment(self):
        report_file = BytesIO(b'fake xlsx content')
        mail_service.send_report('test@example.com', 2024, report_file)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['test@example.com'])
        self.assertEqual(len(message.attachments), 1)
        filename, content, mimetype = message.attachments[0]
        self.assertEqual(filename, 'Отчёт о раздачах за 2024 год.xlsx')
        self.assertEqual(content, b'fake xlsx content')
        self.assertEqual(
            mimetype,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


class ReportMonthTests(TestCase):
    """Тесты веток report._report_month()."""

    def _today(self, year, month, day):
        m = mock.patch('press.services.report.datetime')
        mocked = m.start()
        self.addCleanup(m.stop)
        mocked.date.today.return_value = datetime.date(year, month, day)
        return mocked

    def test_january_before_4th_returns_december_previous_year(self):
        """
        В январе до 4-го числа возвращается декабрь ТОГО ЖЕ года
        (replace(month=12) без уменьшения года). Известная проблема;
        тест фиксирует текущее поведение.
        """
        self._today(2024, 1, 2)
        self.assertEqual(report._report_month(), datetime.date(2024, 12, 1))

    def test_before_4th_returns_previous_month(self):
        self._today(2024, 5, 3)
        self.assertEqual(report._report_month(), datetime.date(2024, 4, 1))

    def test_from_4th_returns_current_month(self):
        self._today(2024, 5, 4)
        self.assertEqual(report._report_month(), datetime.date(2024, 5, 1))


class ReportContentTests(PressBaseTestCase):
    """Тесты содержимого и граничных случаев generate_report()."""

    def _make_distribution(self, date, with_number=True):
        distribution = Distribution.objects.create(
            distribution_date=date,
            autor=self.user,
            factory=self.factory,
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
        )
        if with_number:
            NewspaperNumbersOnDistribution.objects.create(
                distribution=distribution, number=self.number, quantity=10)
        DistributionPartyMembers.objects.create(
            distribution=distribution, member=self.party_member, quantity=10)
        return distribution

    def _xlsx_text(self, result):
        """Собирает текстовое содержимое xlsx: имена листов + shared strings."""
        with zipfile.ZipFile(result) as archive:
            workbook = archive.read('xl/workbook.xml').decode('utf-8')
            strings = archive.read('xl/sharedStrings.xml').decode('utf-8')
        return workbook + strings

    def test_report_sheet_names(self):
        result = report.generate_report(report_month=datetime.date(2024, 1, 1))
        text = self._xlsx_text(result)
        for sheet in ('Общие данные', 'Распространители', 'Предприятия'):
            self.assertIn(sheet, text)

    def test_report_contains_member_and_factory(self):
        self._make_distribution(datetime.date(2024, 2, 10))
        result = report.generate_report(report_month=datetime.date(2024, 2, 1))
        text = self._xlsx_text(result)
        self.assertIn('Петров Пётр', text)
        self.assertIn('Завод имени Ленина', text)

    def test_report_with_multiple_numbers_on_distribution(self):
        """Ветка numbers.count() > 1: несколько номеров в одной раздаче."""
        second_number = NewspaperNumber.objects.create(
            newspaper=self.newspaper, number='2', year=datetime.date(2024, 2, 1))
        distribution = self._make_distribution(datetime.date(2024, 2, 10))
        NewspaperNumbersOnDistribution.objects.create(
            distribution=distribution, number=second_number, quantity=5)
        result = report.generate_report(report_month=datetime.date(2024, 2, 1))
        text = self._xlsx_text(result)
        self.assertIn('Пр №1, Пр №2', text)

    def test_report_with_sympathizer(self):
        distribution = self._make_distribution(datetime.date(2024, 2, 10))
        DistributionSympathizerMember.objects.create(
            distribution=distribution, member=self.sympathizer, quantity=10)
        result = report.generate_report(report_month=datetime.date(2024, 2, 1))
        text = self._xlsx_text(result)
        self.assertIn('соч. Сидоров Алексей', text)

    def test_report_december_year_boundary(self):
        """Декабрь: переход диапазона на следующий год."""
        distribution = self._make_distribution(datetime.date(2024, 12, 10))
        result = report.generate_report(report_month=datetime.date(2024, 12, 1))
        self.assertIsInstance(result, BytesIO)
        self.assertIn('10.12.2024', self._xlsx_text(result))


class ManagementCommandExtraTests(PressBaseTestCase):
    """Дополнительные тесты management-команды send_report."""

    @override_settings(REPORT_MONTH_EMAIL=None)
    def test_send_report_command_without_email(self):
        from press.management.commands.send_report import Command
        with self.assertRaises(CommandError):
            Command().handle()


class ViewsExtraTests(PressBaseTestCase):
    """Дополнительные тесты view press: HTMX-ветки, ошибки форм, алгоритм распределения."""

    def _make_distribution(self, date=None, factory=None):
        return Distribution.objects.create(
            distribution_date=date or datetime.date.today(),
            autor=self.user,
            factory=factory or self.factory,
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
        )

    def _distrib_post(self, **overrides):
        data = {
            'distribution_date': '2024-01-15',
            'factory': self.factory.pk,
            'start_time': '10:00',
            'end_time': '12:00',
            'newspaper': [self.number.pk],
            'newspaper-quantity': ['10'],
        }
        data.update(overrides)
        return self.client.post(reverse('press:new-distrib'), data)

    def test_my_distribution_htmx_get(self):
        """HTMX-запрос возвращает только блок таблицы, без полной страницы."""
        self._make_distribution()
        response = self.client.get(reverse('press:all'), HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'<html', response.content)

    def test_my_distribution_post_filter_by_factory(self):
        other_factory = FactoryPoint.objects.create(title='Другой завод', town=self.town)
        self._make_distribution()
        self._make_distribution(factory=other_factory)
        response = self.client.post(reverse('press:all'), {'factory': str(self.factory.pk)})
        self.assertEqual(response.status_code, 200)
        self.assertIn('Завод имени Ленина', response.content.decode())
        self.assertNotIn('Другой завод', response.content.decode())

    def test_my_distribution_post_empty_values(self):
        """Пустые значения фильтров отбрасываются."""
        self._make_distribution()
        response = self.client.post(reverse('press:all'), {
            'distribution_date': '',
            'factory': '',
        })
        self.assertEqual(response.status_code, 200)

    def test_new_distrib_remainder_to_party_members(self):
        """Остаток от деления уходит членам партии: 11 газет на 2 раздающих = 6 и 5."""
        second_member = _get_user_model().objects.create_user(
            email='party2@example.com', password='pass1234', party_member=True)
        response = self._distrib_post(
            **{'party_members': [self.party_member.pk, second_member.pk],
               'newspaper-quantity': ['11']})
        self.assertEqual(response.status_code, 200)
        distribution = Distribution.objects.get(factory=self.factory)
        quantities = {
            line.member_id: line.quantity
            for line in DistributionPartyMembers.objects.filter(distribution=distribution)
        }
        self.assertEqual(quantities[self.party_member.pk], 6)
        self.assertEqual(quantities[second_member.pk], 5)
        self.assertEqual(sum(quantities.values()), 11)

    def test_new_distrib_remainder_to_sympathizers(self):
        """Остаток от деления уходит сочувствующим: 11 газет на 2 раздающих = 6 и 5."""
        second_sympathizer = Sympathizer.objects.create(name='Козлов Иван')
        response = self._distrib_post(
            **{'sympathizer-members': [self.sympathizer.name, second_sympathizer.name],
               'newspaper-quantity': ['11']})
        self.assertEqual(response.status_code, 200)
        distribution = Distribution.objects.get(factory=self.factory)
        quantities = {
            line.member_id: line.quantity
            for line in DistributionSympathizerMember.objects.filter(distribution=distribution)
        }
        self.assertEqual(quantities[self.sympathizer.pk], 6)
        self.assertEqual(quantities[second_sympathizer.pk], 5)
        self.assertEqual(sum(quantities.values()), 11)

    def test_new_distrib_creates_new_sympathizer(self):
        """Неизвестное имя сочувствующего создаёт новую запись Sympathizer."""
        response = self._distrib_post(**{'sympathizer-members': ['Новый Человек']})
        self.assertEqual(response.status_code, 200)
        sympathizer = Sympathizer.objects.get(name='Новый Человек')
        distribution = Distribution.objects.get(factory=self.factory)
        self.assertTrue(DistributionSympathizerMember.objects.filter(
            distribution=distribution, member=sympathizer).exists())

    def test_new_distrib_sympathizer_dedup_by_normalized_name(self):
        """Имя с лишними пробелами/знаками матчится с существующим, дубль не создаётся."""
        response = self._distrib_post(**{'sympathizer-members': [' Сидоров  Алексей,']})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Sympathizer.objects.count(), 1)

    def test_new_distrib_multiple_newspapers(self):
        second_number = NewspaperNumber.objects.create(
            newspaper=self.newspaper, number='2', year=datetime.date(2024, 1, 1))
        response = self._distrib_post(**{
            'party_members': [self.party_member.pk],
            'newspaper': [self.number.pk, second_number.pk],
            'newspaper-quantity': ['10', '5'],
        })
        self.assertEqual(response.status_code, 200)
        distribution = Distribution.objects.get(factory=self.factory)
        self.assertEqual(
            NewspaperNumbersOnDistribution.objects.filter(distribution=distribution).count(), 2)

    def test_new_distrib_post_no_newspapers_current_behavior(self):
        """
        Без газет форма невалидна, view не возвращает HttpResponse.
        Тест фиксирует текущее поведение.
        """
        with self.assertRaises(ValueError):
            self._distrib_post(**{'party_members': [self.party_member.pk],
                                  'newspaper': [], 'newspaper-quantity': []})
        self.assertFalse(Distribution.objects.filter(factory=self.factory).exists())

    def test_new_distrib_post_mismatched_newspapers_current_behavior(self):
        """
        Рассинхрон списков газет и количеств: форма невалидна,
        view не возвращает HttpResponse. Тест фиксирует текущее поведение.
        """
        second_number = NewspaperNumber.objects.create(
            newspaper=self.newspaper, number='2', year=datetime.date(2024, 1, 1))
        with self.assertRaises(ValueError):
            self._distrib_post(**{'party_members': [self.party_member.pk],
                                  'newspaper': [self.number.pk, second_number.pk],
                                  'newspaper-quantity': ['10']})
        self.assertFalse(Distribution.objects.filter(factory=self.factory).exists())

    def test_hx_distrib_delete_missing_pk(self):
        response = self.client.delete(reverse('press:hx-distrib', kwargs={'pk': 9999}))
        self.assertEqual(response.status_code, 404)

    def test_report_generate_post_without_email(self):
        response = self.client.post(reverse('press:report-generate'), {
            'report-year': '2024',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_report_generate_post_current_year(self):
        """Год равен текущему: отчёт формируется по текущий месяц включительно."""
        response = self.client.post(reverse('press:report-generate'), {
            'report-year': str(datetime.date.today().year),
            'report-email': 'boss@example.com',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

    def test_towns_delete_missing_pk_current_behavior(self):
        """
        Town.objects.get(pk=...) бросает DoesNotExist вместо 404.
        Известная проблема; тест фиксирует текущее поведение.
        """
        with self.assertRaises(Town.DoesNotExist):
            self.client.delete(reverse('press:towns-delete', kwargs={'pk': 9999}))

    def test_factory_post_invalid_form_current_behavior(self):
        """
        Невалидная форма: склейка ошибок через "\\n".join(ErrorList) падает
        с TypeError. Известная проблема; тест фиксирует текущее поведение.
        """
        with self.assertRaises(TypeError):
            self.client.post(reverse('press:factory'), {'title': 'Без города'})
        self.assertFalse(FactoryPoint.objects.filter(title='Без города').exists())

    def test_factory_delete_missing_id_current_behavior(self):
        """
        FactoryPoint.objects.get(pk=...) бросает DoesNotExist вместо 404
        (проверка `fabric is None` недостижима). Тест фиксирует текущее поведение.
        """
        with self.assertRaises(FactoryPoint.DoesNotExist):
            self.client.delete(f"{reverse('press:factory')}?id=9999")

    def test_newspaper_post_empty_short_title_current_behavior(self):
        """
        Проверка short_title.strip == '' без вызова метода не срабатывает,
        пустое краткое название сохраняется. Тест фиксирует текущее поведение.
        """
        response = self.client.post(reverse('press:newspaper'), {
            'title': 'Известия',
            'short-title': '',
        })
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Newspaper.objects.filter(title='Известия', short_title='').exists())

    def test_newspaper_delete_no_id(self):
        response = self.client.delete(reverse('press:newspaper'))
        self.assertEqual(response.status_code, 404)

    def test_newspaper_numbers_post_invalid_form(self):
        response = self.client.post(reverse('press:newspaper-numbers'), {
            'newspaper': '',
            'number': '99',
            'year': '2024-06',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('Исправьте следующие ошибки', response.content.decode())
        self.assertFalse(NewspaperNumber.objects.filter(number='99').exists())

    def test_newspaper_numbers_delete_no_id(self):
        response = self.client.delete(reverse('press:newspaper-numbers'))
        self.assertEqual(response.status_code, 404)

    def test_login_required_on_all_press_views(self):
        self.client.logout()
        urls = [
            reverse('press:all'),
            reverse('press:new-distrib'),
            reverse('press:hx-newspaper-field'),
            reverse('press:report-generate'),
            reverse('press:towns'),
            reverse('press:factory'),
            reverse('press:newspaper'),
            reverse('press:newspaper-numbers'),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith('/login/'))


class DeprecatedViewsExtraTests(PressBaseTestCase):
    """Дополнительные тесты deprecated view (ветки фильтрации и сессии)."""

    def test_new_party_member_distrib_excludes_selected(self):
        """Все члены партии уже выбраны: 204 без контента."""
        response = self.client.post(reverse('press:htmx-add-party-member'), {
            'party-members': [str(self.user.pk), str(self.party_member.pk)],
        })
        self.assertEqual(response.status_code, 204)

    def test_new_sympathizer_distrib_filters_selected(self):
        response = self.client.post(reverse('press:htmx-add-sympathizer'), {
            'sympathizer-members': [self.sympathizer.name],
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Сидоров Алексей', response.content.decode())

    def test_hx_add_party_member_without_id(self):
        response = self.client.post(reverse('press:hx-add-party-member'), {})
        self.assertEqual(response.status_code, 204)

    def test_hx_delete_party_member_selected_in_session(self):
        session = self.client.session
        session['select_party_members'] = [str(self.party_member.pk)]
        session.save()
        response = self.client.delete(
            reverse('press:hx-delete-pary-member', kwargs={'id_delete_member': self.party_member.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session.get('select_party_members'), [])
