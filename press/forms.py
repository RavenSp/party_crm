from django.forms.models import ModelForm
from django import forms
from .models import NewspaperNumber, Distribution


class DistributionForm(ModelForm):
    class Meta:
        model = Distribution
        fields = ['distribution_date', 'factory', 'start_time', 'end_time', 'description']



class NewspapersNumberForm(ModelForm):
    class Meta:
        model = NewspaperNumber
        fields = ['newspaper', 'number', 'year']
