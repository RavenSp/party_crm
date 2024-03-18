from django.contrib import admin
from .models import Newspaper, NewspaperNumber, Town, FactoryPoint, Distribution, Sympathizer
# Register your models here.

admin.site.register(Newspaper)
admin.site.register(NewspaperNumber)
admin.site.register(Town)
admin.site.register(FactoryPoint)
admin.site.register(Distribution)
admin.site.register(Sympathizer)