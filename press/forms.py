from django.forms.models import ModelForm
from django import forms
from .models import Newspaper, NewspaperNumber, Town, Distribution, FactoryPoint


class DistributionForm(ModelForm):
    class Meta:
        model = Distribution
        fields = ['distribution_date', 'factory', 'start_time', 'end_time', 'description']


class FabricForm(ModelForm):
    class Meta:
        model = FactoryPoint
        fields = ['town', 'title', 'description']


class NewspapersNumberForm(ModelForm):
    year = forms.IntegerField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    newspaper_number = forms.IntegerField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    class Meta:
        model = NewspaperNumber
        fields = ['newspaper', 'number', 'year']
