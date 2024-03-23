from django.urls import path
from .views import my_distribution, new_distrib, new_party_member_distrib, new_sympathizer_distrib, hx_add_party_member, hx_delete_party_member, hx_newspaper

urlpatterns = [
    path('', my_distribution, name='all'),
    path('new-distrib/', new_distrib, name='new-distrib'),
    path('htmx-add-party-member/', new_party_member_distrib, name='htmx-add-party-member'),
    path('htmx-add-sympathizer/', new_sympathizer_distrib, name='htmx-add-sympathizer'),
    path('hx-add-party-member/', hx_add_party_member, name='hx-add-party-member'),
    path('hx-delete-pary-member/<int:id_delete_member>/', hx_delete_party_member, name='hx-delete-pary-member'),
    path('hx-newspaper-field/', hx_newspaper, name='hx-newspaper-field'),
]
