from django.dispatch import receiver
from django.db.models.signals import post_save
from person.models import Person
from django.contrib.auth.models import User


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Person.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.Person.save()