from press.models import Distribution, DistributionPartyMembers, DistributionSympathizerMember, NewspaperNumbersOnDistribution


def get_all(filter_by):
    distrib_list = Distribution.objects.filter(**filter_by).all()
    if len(distrib_list) == 0:
        return []
    return [x.__dict__ for x in distrib_list]
