# Файл для объединения бизнес-логики работы с газетами
from typing import Optional, List
from press.models import Newspaper, NewspaperNumber
from django.db.models import QuerySet


def add_newspaper(title: str, short_title: str) -> int:
    newspaper = Newspaper(
        title=title,
        short_title=short_title
    )
    newspaper.save()
    return newspaper.id


def edit_newspaper(id: int, title: str = None, short_title: str = None) -> dict:
    newspaper = Newspaper.objects.get(pk=id)
    if title:
        newspaper.title = title
    if short_title:
        newspaper.short_title =short_title
    newspaper.save()
    return newspaper.__dict__


def get_newspaper_by_id(id: int) -> dict:
    newspaper = Newspaper.objects.get(pk=id)
    return newspaper.__dict__


def get_all_newspapers(filter_by: dict = None) -> List[dict]:
    newspapers = Newspaper.objects
    if filter_by:
        newspapers = newspapers.filter(**filter_by).all()
    return [x.__dict__ for x in newspapers]
