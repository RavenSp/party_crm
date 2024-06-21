from press.models import Distribution, DistributionPartyMembers, DistributionSympathizerMember, NewspaperNumbersOnDistribution


def get_all(filter_by):
    distrib_list = Distribution.objects.filter(**filter_by).prefetch_related('numbers') \
        .prefetch_related('numbers__number') \
        .prefetch_related('numbers__number__newspaper')\
        .prefetch_related('party_members') \
        .prefetch_related('party_members__member') \
        .prefetch_related('sympathizer_members') \
        .prefetch_related('sympathizer_members__member') \
        .select_related('factory')\
        .prefetch_related('factory__town')\
        .order_by('-distribution_date', '-start_time')\
        .all()
    if len(distrib_list) == 0:
        return []
    return distrib_list
