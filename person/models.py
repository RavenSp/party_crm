from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager


class PartyOrganization(models.Model):
    title = models.CharField(verbose_name='Наименование парт. организации', max_length=255)

    def __str__(self):
        return str(self.title)


class Person(AbstractUser):
    username = None
    email = models.EmailField(_("email address"), unique=True)

    bio = models.TextField(verbose_name='Биография', blank=True, null=True)
    party_member = models.BooleanField(verbose_name='Член партии', default=True)
    party_ticket_number = models.CharField(verbose_name='Номер партбилета', max_length=255, blank=True, null=True)
    party_organization = models.ForeignKey(to=PartyOrganization, verbose_name='Партйиная организация', blank=True, null=True, on_delete=models.SET_NULL)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    def set_party_organization(self, party_organization: PartyOrganization):
        if not self.party_member:
            raise ValueError('Чтобы добавить человека в партийную организацию он должен быть челном партии!')
        self.party_organization = party_organization


    @property
    def full_name(self):
        if self.last_name or self.first_name:
            return " ".join([self.last_name, self.first_name])
        else:
            return self.email

