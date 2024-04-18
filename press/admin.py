from django.contrib import admin
from .models import Newspaper, NewspaperNumber, Town, FactoryPoint, Distribution, Sympathizer, NewspaperNumbersOnDistribution, DistributionPartyMembers, DistributionSympathizerMember
# Register your models here.

admin.site.register(Newspaper)
admin.site.register(NewspaperNumber)
admin.site.register(Town)
admin.site.register(FactoryPoint)
admin.site.register(Distribution)
admin.site.register(Sympathizer)
admin.site.register(NewspaperNumbersOnDistribution)
admin.site.register(DistributionPartyMembers)
admin.site.register(DistributionSympathizerMember)