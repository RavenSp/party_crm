from django.db import models


class Town(models.Model):
    title = models.CharField(verbose_name='Город', max_length=255)

    def __str__(self):
        return str(self.title)

    class Meta:
        verbose_name = 'Город'
        verbose_name_plural = 'Города'


class FactoryPoint(models.Model):
    title = models.CharField(verbose_name='Наименование предприятия', max_length=255)
    description = models.TextField(blank=True, null=True, verbose_name='Примечание')
    town = models.ForeignKey(to=Town, verbose_name='Город расположения', related_name='factories', on_delete=models.PROTECT)
    geo_lat = models.FloatField(verbose_name='Широта', blank=True, null=True)
    geo_lon = models.FloatField(verbose_name='Долгота', blank=True, null=True)

    def __str__(self):
        return str(self.title)

    class Meta:
        verbose_name = 'Предприятие'
        verbose_name_plural = 'Предприятия'