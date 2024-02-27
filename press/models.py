from django.db import models
from person.models import Person

class Newspaper(models.Model):
    title = models.CharField(verbose_name='Название газеты', max_length=255)

    def __str__(self):
        return str(self.title)

    class Meta:
        verbose_name = 'Газета'
        verbose_name_plural = 'Газеты'


class NewspaperNumber(models.Model):
    newspaper = models.ForeignKey(to=Newspaper, verbose_name='Газета')
    number = models.CharField(verbose_name='Номер', max_length=255)
    year = models.DateField(verbose_name='Год и месяц выхода', null=True, blank=True)

    # Вероятно сюда можно будет потом добавить и файл газеты

    class Meta:
        verbose_name = 'Номер газеты'
        verbose_name_plural = 'Номера газет'

    def __str__(self):
        return f"{self.newspaper.title} {self.number}"


class Town(models.Model):
    title = models.CharField(verbose_name='Город', max_length=255)

    def __str__(self):
        return str(self.title)

    class Meta:
        verbose_name = 'Город'
        verbose_name_plural = 'Города'


class Factory(models.Model):
    title = models.CharField(verbose_name='Наименование предприятия', max_length=255)
    description = models.TextField(blank=True, null=True, verbose_name='Примечание')
    town = models.ForeignKey(to=Town, verbose_name='Город расположения', related_name='factories')

    def __str__(self):
        return str(self.title)

    class Meta:
        verbose_name = 'Предприятие'
        verbose_name_plural = 'Предприятия'


class Distribution(models.Model):
    distribution_date = models.DateField(verbose_name='Дата раздачи')
    autor = models.ForeignKey(to=Person, verbose_name='Автор записи')
    factory = models.ForeignKey(to=Factory, verbose_name='Предприятие')
    start_time = models.TimeField(verbose_name='Начало раздачи')
    end_time = models.TimeField(verbose_name='Окончание раздачи')
    description = models.TextField(blank=True, null=True, verbose_name='Примечание')


class NewspaperNumbersOnDistribution(models.Model):
    number = models.ForeignKey(to=NewspaperNumber, verbose_name='Номер газеты')
    quantity = models.IntegerField(verbose_name='Количество')


