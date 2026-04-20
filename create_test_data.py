import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from clinica.models import Fonoaudiologo, Paciente, MaterialDidatico

def run():
    # 1. Criar Superuser (Admin)
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin')
        print("Superuser 'admin' (senha: admin) criado com sucesso.")

    # 2. Criar Fonoaudiólogo
    if not User.objects.filter(username='fono').exists():
        user_fono = User.objects.create_user(username='fono', password='123', first_name='Dr. Silva')
        fono = Fonoaudiologo.objects.create(
            user=user_fono,
            crfa='12345-SP',
            telefone='(11) 99999-9999',
            especialidade='Linguagem Infantil'
        )
        print("Fonoaudiólogo 'fono' (senha: 123) criado com sucesso.")
    else:
        fono = Fonoaudiologo.objects.get(user__username='fono')

    # 3. Criar Paciente
    if not User.objects.filter(username='paciente').exists():
        user_paciente = User.objects.create_user(username='paciente', password='123', first_name='Joãozinho')
        paciente = Paciente.objects.create(
            user=user_paciente,
            fonoaudiologo=fono,
            nome='Joãozinho Silva',
            data_nascimento=date(2015, 5, 10),
            cpf='111.222.333-44',
            nome_responsavel='Maria Silva',
            historico_clinico='Atraso no desenvolvimento da fala.'
        )
        print("Paciente 'paciente' (senha: 123) criado com sucesso.")

if __name__ == '__main__':
    run()
