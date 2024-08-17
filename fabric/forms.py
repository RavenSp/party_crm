from django.forms.models import ModelForm
from django import forms

from fabric.models import FactoryPoint


class FabricForm(ModelForm):
    class Meta:
        model = FactoryPoint
        fields = ['town', 'title', 'description']