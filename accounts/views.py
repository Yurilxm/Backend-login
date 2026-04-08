from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .models import User
from .serializers import (
    UserSerializer,
    RegisterSerializer,
    TwoFactorVerifySerializer,
    LoginSerializer,
    generate_qr_code_base64
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    Registro de usuário
    POST /signup/
    """
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.save()
        
        # Gera QR Code
        totp_uri = user.get_totp_uri()
        qr_code_base64 = generate_qr_code_base64(totp_uri) if totp_uri else None
        
        return Response({
            'message': 'Usuário criado com sucesso. Configure 2FA.',
            'qr_code': qr_code_base64
        }, status=status.HTTP_201_CREATED)


class TwoFactorVerifyView(APIView):
    """
    Verificação de 2FA
    POST /2fa/verify/
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = TwoFactorVerifySerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = serializer.context['user']
        
        # Ativa 2FA
        user.is_2fa_enabled = True
        user.save(update_fields=['is_2fa_enabled'])
        
        return Response({
            'message': '2FA configurado com sucesso. Aguarde aprovação do administrador.',
            'is_2fa_enabled': True
        }, status=status.HTTP_200_OK)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        email = request.data.get('username')
        password = request.data.get('password')

        # ✅ Checa inativo ANTES do serializer, evitando o wrapper do DRF
        try:
            user = User.objects.get(email=email)
            if user.check_password(password) and not user.is_active:
                return Response(
                    {'error': 'account_inactive'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except User.DoesNotExist:
            pass  # Deixa o serializer tratar "email ou senha inválidos"

        serializer = LoginSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.context['user']
        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)


class MeView(generics.RetrieveAPIView):
    """
    Usuário logado
    GET /signup/me/
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user