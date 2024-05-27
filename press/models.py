from django.db import models
from person.models import Person
from helpers.common import name_normalizer


class Newspaper(models.Model):
    title = models.CharField(verbose_name='Название газеты', max_length=255)
    short_title = models.CharField(verbose_name='Краткое название', max_length=10)
    

    def __str__(self):
        return str(self.title)

    class Meta:
        verbose_name = 'Газета'
        verbose_name_plural = 'Газеты'


class NewspaperNumber(models.Model):
    newspaper = models.ForeignKey(to=Newspaper, verbose_name='Газета', on_delete=models.PROTECT, related_name='newspaper')
    number = models.CharField(verbose_name='Номер', max_length=255)
    year = models.DateField(verbose_name='Год и месяц выхода', null=True, blank=True)

    # Вероятно сюда можно будет потом добавить и файл газеты

    class Meta:
        verbose_name = 'Номер газеты'
        verbose_name_plural = 'Номера газет'

    def __str__(self):
        return f"{self.newspaper.title} {self.number}"


# Есть мысль, что этой сущности не место в этом приложении. Возможно стоит вынести её отсюда.
class Sympathizer(models.Model):
    name = models.CharField(verbose_name='Имя сочувствующего', max_length=255)

    class Meta:
        verbose_name = 'Сочувствующий'
        verbose_name_plural = 'Сочувствующие'

    @property
    def normalize_name(self):
        return name_normalizer(self.name)

    def __str__(self):
        return f"соч. {self.name}"


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


class Distribution(models.Model):
    distribution_date = models.DateField(verbose_name='Дата раздачи')
    autor = models.ForeignKey(to=Person, verbose_name='Автор записи', on_delete=models.PROTECT)
    factory = models.ForeignKey(to=FactoryPoint, verbose_name='Предприятие', on_delete=models.PROTECT)
    start_time = models.TimeField(verbose_name='Начало раздачи')
    end_time = models.TimeField(verbose_name='Окончание раздачи')
    description = models.TextField(blank=True, null=True, verbose_name='Примечание')

    class Meta:
        verbose_name = 'Раздача'
        verbose_name_plural = 'Раздачи'

    def count_members(self):
        return len(self.party_members) + len(self.sympathizer_members)

    def __str__(self):
        return f"Раздача {self.distribution_date.strftime('%d.%m.%Y')} на {self.factory.title}"


class NewspaperNumbersOnDistribution(models.Model):
    distribution = models.ForeignKey(to=Distribution, verbose_name='Раздача', related_name='numbers', on_delete=models.CASCADE)
    number = models.ForeignKey(to=NewspaperNumber, verbose_name='Номер газеты', related_name='distributions', on_delete=models.PROTECT)
    quantity = models.IntegerField(verbose_name='Количество')

    def __str__(self):
        return f"Номер в раздаче ID {self.pk}"


class DistributionPartyMembers(models.Model):
    member = models.ForeignKey(to=Person, verbose_name='Раздающий', related_name='distributions', on_delete=models.PROTECT)
    distribution = models.ForeignKey(to=Distribution, verbose_name='Раздача', related_name='party_members', on_delete=models.CASCADE)

    def __str__(self):
        return f"Член партии на раздаче ID {self.pk}"


class DistributionSympathizerMember(models.Model):
    member = models.ForeignKey(to=Sympathizer, verbose_name='Раздающий сочувствующий', related_name='distributions', on_delete=models.PROTECT)
    distribution = models.ForeignKey(to=Distribution, verbose_name='Раздача', related_name='sympathizer_members', on_delete=models.CASCADE)

    def __str__(self):
        return f"Сочувствующий на раздаче ID {self.pk}"
