import datetime

from django.test import TestCase, Client, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.urls import reverse

from person.forms import CustomUserChangeForm, CustomUserCreationForm
from person.models import PartyOrganization, Person
from person.services.login import auth_user


class UsersManagersTests(TestCase):
    """Тесты кастомного менеджера пользователей."""

    def test_create_user(self):
        user = Person.objects.create_user(email='normal@user.com', password='foo')
        self.assertEqual(user.email, 'normal@user.com')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        try:
            self.assertIsNone(user.username)
        except AttributeError:
            pass
        with self.assertRaises(TypeError):
            Person.objects.create_user()
        with self.assertRaises(TypeError):
            Person.objects.create_user(email='')
        with self.assertRaises(ValueError):
            Person.objects.create_user(email='', password="foo")

    def test_create_superuser(self):
        admin_user = Person.objects.create_superuser('super@user.com', 'foo')
        self.assertEqual(admin_user.email, 'super@user.com')
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        try:
            self.assertIsNone(admin_user.username)
        except AttributeError:
            pass
        with self.assertRaises(ValueError):
            Person.objects.create_superuser(
                email='super@user.com', password='foo', is_superuser=False)
        with self.assertRaises(ValueError):
            Person.objects.create_superuser(
                email='super2@user.com', password='foo', is_staff=False)


class PersonModelTests(TestCase):
    """Тесты модели Person."""

    def test_full_name_with_last_and_first(self):
        user = Person.objects.create_user(
            email='test@example.com',
            password='pass',
            last_name='Иванов',
            first_name='Иван',
        )
        self.assertEqual(user.full_name, 'Иванов Иван')

    def test_full_name_without_names(self):
        user = Person.objects.create_user(email='noname@example.com', password='pass')
        self.assertEqual(user.full_name, 'noname@example.com')

    def test_full_name_only_last_name(self):
        """Только фамилия: текущее поведение — хвостовой пробел."""
        user = Person.objects.create_user(
            email='last@example.com', password='pass', last_name='Иванов')
        self.assertEqual(user.full_name, 'Иванов ')

    def test_full_name_only_first_name(self):
        """Только имя: текущее поведение — ведущий пробел."""
        user = Person.objects.create_user(
            email='first@example.com', password='pass', first_name='Иван')
        self.assertEqual(user.full_name, ' Иван')

    def test_str_returns_email(self):
        user = Person.objects.create_user(email='str@example.com', password='pass')
        self.assertEqual(str(user), 'str@example.com')

    def test_set_party_organization_for_member(self):
        org = PartyOrganization.objects.create(title='Московская организация')
        user = Person.objects.create_user(
            email='member@example.com',
            password='pass',
            party_member=True,
        )
        user.set_party_organization(org)
        user.save()
        self.assertEqual(user.party_organization, org)

    def test_set_party_organization_for_non_member_raises(self):
        org = PartyOrganization.objects.create(title='Московская организация')
        user = Person.objects.create_user(
            email='nonmember@example.com',
            password='pass',
            party_member=False,
        )
        with self.assertRaises(ValueError):
            user.set_party_organization(org)


class PartyOrganizationModelTests(TestCase):
    """Тесты модели PartyOrganization."""

    def test_str(self):
        org = PartyOrganization.objects.create(title='Тестовая организация')
        self.assertEqual(str(org), 'Тестовая организация')


class LoginServiceTests(TestCase):
    """Тесты сервиса аутентификации."""

    def setUp(self):
        self.user = Person.objects.create_user(email='login@example.com', password='secret')
        self.factory = RequestFactory()

    def _request(self):
        request = self.factory.post('/login/')
        SessionMiddleware(lambda req: None).process_request(request)
        request.session.save()
        return request

    def test_auth_user_success(self):
        request = self._request()
        response = auth_user(request, email='login@example.com', password='secret')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('person:profile'))

    def test_auth_user_failure(self):
        request = self._request()
        response = auth_user(request, email='login@example.com', password='wrong')
        self.assertEqual(response.status_code, 200)


class PersonViewsTests(TestCase):
    """Тесты view приложения person."""

    def setUp(self):
        self.user = Person.objects.create_user(
            email='view@example.com',
            password='pass1234',
            last_name='Иванов',
            first_name='Иван',
            party_member=True,
        )
        self.client = Client()

    def test_login_view_redirects_authenticated(self):
        self.client.login(email='view@example.com', password='pass1234')
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/profile/')

    def test_login_view_get(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_login_view_post_success(self):
        response = self.client.post(reverse('login'), {
            'email': 'view@example.com',
            'password': 'pass1234',
        })
        self.assertEqual(response.status_code, 302)

    def test_login_view_post_failure(self):
        response = self.client.post(reverse('login'), {
            'email': 'view@example.com',
            'password': 'wrong',
        })
        self.assertEqual(response.status_code, 200)

    def test_profile_view_for_party_member(self):
        self.client.login(email='view@example.com', password='pass1234')
        response = self.client.get(reverse('person:profile'))
        self.assertEqual(response.status_code, 200)

    def test_profile_view_for_non_party_member_with_sympathizer(self):
        from press.models import Sympathizer, Distribution, DistributionSympathizerMember, FactoryPoint, Town
        non_member = Person.objects.create_user(
            email='symp@example.com',
            password='pass1234',
            last_name='Сидоров',
            first_name='Алексей',
            party_member=False,
        )
        Sympathizer.objects.create(name='Сидоров Алексей')
        self.client.login(email='symp@example.com', password='pass1234')
        response = self.client.get(reverse('person:profile'))
        self.assertEqual(response.status_code, 200)

    def test_profile_view_requires_login(self):
        response = self.client.get(reverse('person:profile'))
        self.assertEqual(response.status_code, 302)

    def test_logout_view(self):
        self.client.login(email='view@example.com', password='pass1234')
        response = self.client.get(reverse('person:logout'))
        self.assertEqual(response.status_code, 302)

    def test_login_view_post_without_fields(self):
        """POST без полей email/password: ошибка аутентификации, 200."""
        response = self.client.post(reverse('login'), {})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['login_error'])

    def test_profile_view_sums(self):
        """Суммы раздач в профиле члена партии: за месяц и за всё время."""
        from press.models import Distribution, DistributionPartyMembers, FactoryPoint, Town
        town = Town.objects.create(title='Москва')
        factory = FactoryPoint.objects.create(title='Завод', town=town)
        today = datetime.date.today()
        current = Distribution.objects.create(
            distribution_date=today, autor=self.user, factory=factory,
            start_time=datetime.time(10, 0), end_time=datetime.time(12, 0))
        old_date = (today.replace(day=1) - datetime.timedelta(days=1))
        old = Distribution.objects.create(
            distribution_date=old_date, autor=self.user, factory=factory,
            start_time=datetime.time(10, 0), end_time=datetime.time(12, 0))
        DistributionPartyMembers.objects.create(distribution=current, member=self.user, quantity=10)
        DistributionPartyMembers.objects.create(distribution=old, member=self.user, quantity=7)
        self.client.login(email='view@example.com', password='pass1234')
        response = self.client.get(reverse('person:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['sum_my_distrib'], 10)
        self.assertEqual(response.context['sum_all_distrib'], 17)

    def test_profile_view_non_member_without_sympathizer_current_behavior(self):
        """
        Для не-члена партии без записи Sympathizer view падает с AttributeError
        (обращение к .pk у None). Известная проблема; тест фиксирует текущее поведение.
        """
        Person.objects.create_user(
            email='nosymp@example.com',
            password='pass1234',
            last_name='Никто',
            first_name='Николай',
            party_member=False,
        )
        self.client.login(email='nosymp@example.com', password='pass1234')
        with self.assertRaises(AttributeError):
            self.client.get(reverse('person:profile'))


class PersonFormsTests(TestCase):
    """Тесты форм приложения person."""

    def test_creation_form_valid(self):
        form = CustomUserCreationForm(data={
            'email': 'new@example.com',
            'password1': 'ComplexPass123',
            'password2': 'ComplexPass123',
        })
        self.assertTrue(form.is_valid())

    def test_creation_form_password_mismatch(self):
        form = CustomUserCreationForm(data={
            'email': 'new@example.com',
            'password1': 'ComplexPass123',
            'password2': 'OtherPass123',
        })
        self.assertFalse(form.is_valid())

    def test_change_form_valid(self):
        user = Person.objects.create_user(email='change@example.com', password='pass')
        form = CustomUserChangeForm(data={'email': 'changed@example.com'}, instance=user)
        self.assertTrue(form.is_valid())
