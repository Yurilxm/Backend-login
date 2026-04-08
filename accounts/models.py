from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
import pyotp


class UserManager(BaseUserManager):
    """Manager personalizado para User model"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('O email é obrigatório')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser deve ter is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser deve ter is_superuser=True')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Modelo de usuário customizado"""
    
    username = models.CharField(
        'Nome de usuário',
        max_length=150,
        unique=True,
        help_text='Obrigatório. 150 caracteres ou menos. Letras, números e @/./+/-/_ apenas.'
    )
    
    email = models.EmailField(
        'Email',
        unique=True,
        error_messages={
            'unique': 'Este email já está cadastrado.',
        }
    )
    
    first_name = models.CharField('Nome', max_length=150)
    last_name = models.CharField('Sobrenome', max_length=150)
    
    is_active = models.BooleanField(
        'Ativo',
        default=False,
        help_text='Designa se o usuário está ativo. Desmarque ao invés de deletar.'
    )
    
    is_2fa_enabled = models.BooleanField(
        '2FA Habilitado',
        default=False,
        help_text='Designa se o usuário tem 2FA configurado.'
    )
    
    two_factor_secret = models.CharField(
        'Segredo 2FA',
        max_length=255,
        blank=True,
        null=True,
        help_text='Chave secreta para geração de TOTP.'
    )
    
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        """Retorna o nome completo do usuário"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        """Retorna o primeiro nome do usuário"""
        return self.first_name
    
    def generate_totp_secret(self):
        """Gera um novo segredo TOTP"""
        self.two_factor_secret = pyotp.random_base32()
        self.save(update_fields=['two_factor_secret'])
        return self.two_factor_secret
    
    def get_totp_uri(self):
        """Retorna a URI para geração do QR Code"""
        if not self.two_factor_secret:
            return None
        
        totp = pyotp.TOTP(self.two_factor_secret)
        return totp.provisioning_uri(
            name=self.email,
            issuer_name='SeuApp'
        )
    
    def verify_totp(self, code):
        """Verifica se o código TOTP é válido"""
        if not self.two_factor_secret:
            return False
        
        totp = pyotp.TOTP(self.two_factor_secret)
        return totp.verify(code)