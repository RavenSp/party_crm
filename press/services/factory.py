from press.models import FactoryPoint


def get_all(filter_by):
    factory_list = FactoryPoint.objects.filter(**filter_by).select_related('town')\
        .prefetch_related('distributions')\
        .prefetch_related('distributions__numbers')\
        .all()
    if len(factory_list) == 0:
        return []
    return factory_list


