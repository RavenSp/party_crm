from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager


class Person(AbstractUser):
    username = None
    email = models.EmailField(_("email address"), unique=True)

    bio = models.TextField(verbose_name='Биография', blank=True, null=True)
    party_member = models.BooleanField(verbose_name='Член партии', default=True)
    party_ticket_number = models.CharField(verbose_name='Номер партбилета', max_length=255, blank=True, null=True)



    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email

