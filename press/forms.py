from django.forms.models import ModelForm
from .models import Newspaper, NewspaperNumber, Town, Distribution, FactoryPoint


class DistributionForm(ModelForm):
    class Meta:
        model = Distribution
        fields = ['distribution_date', 'factory', 'start_time', 'end_time', 'description']


class FabricForm(ModelForm):
    class Meta:
        model = FactoryPoint
        fields = ['town', 'title', 'description']
