from django.urls import path
from .views import my_distribution, new_distrib, new_party_member_distrib, new_sympathizer_distrib

urlpatterns = [
    path('', my_distribution, name='all'),
    path('new-distrib/', new_distrib, name='new-distrib'),
    path('htmx-add-party-member/', new_party_member_distrib, name='htmx-add-party-member'),
    path('htmx-add-sympathizer/', new_sympathizer_distrib, name='htmx-add-sympathizer')
]
