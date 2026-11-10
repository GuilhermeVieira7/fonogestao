from django.core.management.base import BaseCommand

from clinica.agenda import gerar_consultas_realizadas


class Command(BaseCommand):
    help = ('Leva para o histórico de consultas (aguardando avaliação) todos os agendamentos '
            'confirmados cujo horário de término já passou.')

    def handle(self, *args, **options):
        total = gerar_consultas_realizadas()
        self.stdout.write(self.style.SUCCESS(f'{total} consulta(s) enviada(s) para o histórico.'))
