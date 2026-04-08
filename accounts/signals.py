from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import User

@receiver(post_save, sender=User)
def send_activation_email(sender, instance, created, update_fields, **kwargs):
    """
    Envia email quando o usuário é ativado pelo admin
    """
    # Só envia se:
    # 1. Não é um usuário novo (created=False)
    # 2. O campo is_active foi alterado para True
    # 3. O usuário tem 2FA habilitado
    if not created and instance.is_active and instance.is_2fa_enabled:
        # Verifica se is_active foi realmente alterado
        if update_fields and 'is_active' in update_fields:
            subject = 'Sua conta foi ativada!'
            message = f'''
            Olá {instance.first_name},

            Sua conta no SeuApp foi ativada com sucesso!

            Você já pode fazer login usando seu email e o código do Microsoft Authenticator.

            Acesse: http://localhost:3001/login

            Atenciosamente,
            Equipe SeuApp
            '''
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [instance.email],
                fail_silently=False,
            )