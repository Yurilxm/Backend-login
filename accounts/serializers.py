from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User
import pyotp
import qrcode
import base64
from io import BytesIO


class UserSerializer(serializers.ModelSerializer):
    """Serializer para leitura de dados do usuário"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_2fa_enabled', 'is_active']
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer para registro de usuário"""
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name']
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate_password(self, value):
        """Valida a força da senha"""
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        
        # Validações adicionais
        if len(value) < 8:
            raise serializers.ValidationError('A senha deve ter pelo menos 8 caracteres')
        if len(value) > 64:
            raise serializers.ValidationError('A senha deve ter no máximo 64 caracteres')
        if not any(c.islower() for c in value):
            raise serializers.ValidationError('A senha deve conter pelo menos uma letra minúscula')
        if not any(c.isupper() for c in value):
            raise serializers.ValidationError('A senha deve conter pelo menos uma letra maiúscula')
        if not any(c.isdigit() for c in value):
            raise serializers.ValidationError('A senha deve conter pelo menos um número')
        if not any(c in '!@#$%^&*()_+-=[]{};\':"\\|,.<>/?~' for c in value):
            raise serializers.ValidationError('A senha deve conter pelo menos um caractere especial')
        
        return value
    
    def validate_email(self, value):
        """Valida se o email já existe"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Este email já está cadastrado')
        return value
    
    def validate_username(self, value):
        """Valida se o username já existe"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Este nome de usuário já está em uso')
        return value
    
    def create(self, validated_data):
        """Cria o usuário e gera o segredo TOTP"""
        password = validated_data.pop('password')
        
        # Cria usuário inativo
        user = User.objects.create(
            **validated_data,
            is_active=False,
            is_2fa_enabled=False
        )
        
        user.set_password(password)
        
        # Gera segredo TOTP
        user.two_factor_secret = pyotp.random_base32()
        user.save()
        
        return user


class TwoFactorVerifySerializer(serializers.Serializer):
    """Serializer para verificação de 2FA"""
    
    email = serializers.EmailField(required=True)
    code = serializers.CharField(required=True, max_length=6, min_length=6)
    
    def validate_email(self, value):
        """Valida se o usuário existe"""
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError('Usuário não encontrado')
        
        if user.is_2fa_enabled:
            raise serializers.ValidationError('2FA já está habilitado para este usuário')
        
        if not user.two_factor_secret:
            raise serializers.ValidationError('Segredo 2FA não encontrado')
        
        self.context['user'] = user
        return value
    
    def validate(self, data):
        email = data.get('username')
        password = data.get('password')
        two_factor_code = data.get('two_factor_code', '')

        # Busca o usuário manualmente (authenticate() rejeita inativos antes de chegarmos aqui)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                'non_field_errors': ['Email ou senha inválidos']
            })

        # Verifica a senha manualmente
        if not user.check_password(password):
            raise serializers.ValidationError({
                'non_field_errors': ['Email ou senha inválidos']
            })

        # Agora sim conseguimos checar is_active separadamente
        if not user.is_active:
            raise serializers.ValidationError({
                'error': 'account_inactive'  # ← frontend espera exatamente isso
            })

        # Verifica 2FA se habilitado
        if user.is_2fa_enabled:
            if not two_factor_code:
                raise serializers.ValidationError({
                    'two_factor_code': ['Código 2FA é obrigatório']
                })
            if not user.verify_totp(two_factor_code):
                raise serializers.ValidationError({
                    'two_factor_code': ['Código 2FA inválido']
                })

        self.context['user'] = user
        return data


class LoginSerializer(serializers.Serializer):
    """Serializer para login com 2FA"""
    
    username = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, style={'input_type': 'password'})
    two_factor_code = serializers.CharField(required=False, allow_blank=True, max_length=6)
    
    def validate(self, data):
        """Valida credenciais e 2FA"""
        from django.contrib.auth import authenticate
        
        email = data.get('username')
        password = data.get('password')
        two_factor_code = data.get('two_factor_code', '')
        
        # Autentica usuário
        user = authenticate(username=email, password=password)
        
        if not user:
            raise serializers.ValidationError({
                'non_field_errors': ['Email ou senha inválidos']
            })
        
        # Verifica se está ativo
        if not user.is_active:
            raise serializers.ValidationError({
                'non_field_errors': ['Sua conta aguarda aprovação do administrador']
            })
        
        # Verifica 2FA se habilitado
        if user.is_2fa_enabled:
            if not two_factor_code:
                raise serializers.ValidationError({
                    'two_factor_code': ['Código 2FA é obrigatório']
                })
            
            if not user.verify_totp(two_factor_code):
                raise serializers.ValidationError({
                    'two_factor_code': ['Código 2FA inválido']
                })
        
        self.context['user'] = user
        return data


def generate_qr_code_base64(uri):
    """Gera QR Code em base64 a partir da URI"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"