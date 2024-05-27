from django.contrib import admin
from .models import Newspaper, NewspaperNumber, Town, FactoryPoint, Distribution, Sympathizer, NewspaperNumbersOnDistribution, DistributionPartyMembers, DistributionSympathizerMember
# Register your models here.


class NewspaperNumbersOnDistributionInline(admin.StackedInline):
    model = NewspaperNumbersOnDistribution
    extra = 0
    can_delete = True
    verbose_name = 'Номер газеты'
    verbose_name_plural = 'Номера газет'


class DistributionPartyMembersInline(admin.StackedInline):
    model = DistributionPartyMembers
    extra = 0
    can_delete = True
    verbose_name = 'Член партии'
    verbose_name_plural = 'Члены партии'


class DistributionSympathizerMemberInline(admin.StackedInline):
    model = DistributionSympathizerMember
    extra = 0
    can_delete = True
    verbose_name = 'Сочувствующий'
    verbose_name_plural = 'Сочувствующие'

class DistributionSympathizerMemberAdmin(admin.ModelAdmin):
    model = DistributionSympathizerMember
    inlines = [NewspaperNumbersOnDistributionInline, DistributionPartyMembersInline, DistributionSympathizerMemberInline]

admin.site.register(Newspaper)
admin.site.register(NewspaperNumber)
admin.site.register(Town)
admin.site.register(FactoryPoint)
admin.site.register(Distribution, DistributionSympathizerMemberAdmin)
admin.site.register(Sympathizer)
# admin.site.register(NewspaperNumbersOnDistribution)
# admin.site.register(DistributionPartyMembers)
# admin.site.register(DistributionSympathizerMember)