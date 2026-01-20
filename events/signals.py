from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from .models import Event

@receiver(post_save, sender=User)
def send_activation_email(sender, instance, created, **kwargs):
    if created and not instance.is_active:
        token = default_token_generator.make_token(instance)
        uid = urlsafe_base64_encode(force_bytes(instance.pk))
        activation_link = reverse('activate', kwargs={'uidb64': uid, 'token': token})
        subject = 'Activate your account'
        message = render_to_string('activation_email.html', {
            'user': instance,
            'activation_link': activation_link,
        })
        send_mail(subject, message, 'noreply@example.com', [instance.email])

@receiver(m2m_changed, sender=Event.rsvp_users.through)
def send_rsvp_email(sender, instance, action, pk_set, **kwargs):
    if action == 'post_add':
        for user_id in pk_set:
            user = User.objects.get(pk=user_id)
            subject = f'RSVP Confirmation for {instance.title}'
            message = render_to_string('rsvp_email.html', {
                'user': user,
                'event': instance,
            })
            send_mail(subject, message, 'noreply@example.com', [user.email])
