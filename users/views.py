import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import User

@csrf_exempt
def register(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        email = data.get('email')
        password = data.get('password')

        # Verifica se já existe
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'error': 'Usuário já existe'
            }, status=400)

        # Cria usuário
        user = User.objects.create(
            email=email,
            password=password
        )

        return JsonResponse({
            'message': 'Usuário cadastrado com sucesso!',
            'email': user.email
        })

    return JsonResponse({'error': 'Método inválido'}, status=400)


@csrf_exempt
def login(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        email = data.get('email')
        password = data.get('password')

        try:
            user = User.objects.get(email=email)

            if user.password == password:
                return JsonResponse({
                    'message': 'Login realizado com sucesso!',
                    'email': user.email
                })
            else:
                return JsonResponse({
                    'error': 'Email ou senha inválidos'
                }, status=400)

        except User.DoesNotExist:
            return JsonResponse({
                'error': 'Email ou senha inválidos'
            }, status=400)

    return JsonResponse({'error': 'Método inválido'}, status=400)