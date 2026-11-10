"""Agenda do Dia / do Mês e geração automática do histórico de consultas."""
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from .feriados import feriado
from .models import Agendamento, Consulta

STATUS_SESSAO = 'S'  # sessão registrada no prontuário (modelo Consulta) sem agendamento

ROTULOS_STATUS = {
    'P': 'Pendente',
    'A': 'Confirmado',
    'R': 'Realizado',
    'C': 'Cancelado',
    STATUS_SESSAO: 'Sessão registrada',
}


def gerar_consultas_realizadas(fonoaudiologo=None, paciente=None):
    """
    Leva para o histórico do paciente todo agendamento confirmado cujo horário
    de término já passou. A consulta entra "aguardando avaliação" e o
    agendamento passa a "Realizado". Se o profissional já tinha registrado a
    sessão manualmente no mesmo dia, ela é apenas vinculada (sem duplicar).

    É chamada ao abrir o painel, o prontuário e a área do paciente, e também
    pelo comando `python manage.py gerar_consultas` (para rodar em agendador).
    Retorna quantas consultas foram para o histórico.
    """
    agora = timezone.now()
    agendamentos = Agendamento.objects.filter(status='A', data_hora__lt=agora, consulta__isnull=True)
    if fonoaudiologo is not None:
        agendamentos = agendamentos.filter(fonoaudiologo=fonoaudiologo)
    if paciente is not None:
        agendamentos = agendamentos.filter(paciente=paciente)

    total = 0
    for ag in agendamentos.select_related('paciente'):
        fim = ag.fim
        if fim > agora:
            continue
        inicio = timezone.localtime(ag.data_hora)
        try:
            with transaction.atomic():
                existente = Consulta.objects.select_for_update().filter(
                    paciente=ag.paciente, agendamento__isnull=True, data_hora__date=inicio.date()).first()
                if existente:
                    existente.agendamento = ag
                    existente.hora_fim = existente.hora_fim or fim.time()
                    existente.save(update_fields=['agendamento', 'hora_fim'])
                else:
                    Consulta.objects.create(paciente=ag.paciente, agendamento=ag, data_hora=ag.data_hora,
                                            hora_fim=fim.time())
                Agendamento.objects.filter(pk=ag.pk, status='A').update(status='R')
                total += 1
        except IntegrityError:
            # Outra requisição gerou a mesma consulta ao mesmo tempo: nada a fazer.
            continue
    return total


def itens_agenda(fono, inicio, fim):
    """
    Retorna, em ordem cronológica, tudo o que aconteceu ou vai acontecer na
    agenda do profissional entre as datas `inicio` e `fim` (inclusive):

    * todos os agendamentos (qualquer status, inclusive os criados pelo paciente);
    * as sessões registradas no prontuário que não têm agendamento no mesmo dia
      para o mesmo paciente (assim nada fica de fora e nada aparece duplicado).
    """
    agendamentos = list(
        Agendamento.objects.filter(
            fonoaudiologo=fono,
            data_hora__date__gte=inicio,
            data_hora__date__lte=fim,
        ).select_related('paciente', 'clinica').order_by('data_hora')
    )
    ocupados = {
        (a.paciente_id, timezone.localtime(a.data_hora).date())
        for a in agendamentos if a.status != 'C'
    }
    consultas = Consulta.objects.filter(
        paciente__fonoaudiologo=fono,
        data_hora__date__gte=inicio,
        data_hora__date__lte=fim,
    ).select_related('paciente', 'paciente__clinica').order_by('data_hora')

    itens = []
    for a in agendamentos:
        itens.append({
            'tipo': 'agendamento',
            'id': a.id,
            'data_hora': timezone.localtime(a.data_hora),
            'hora_fim': a.fim.time() if a.hora_fim else None,
            'paciente': a.paciente,
            'clinica': a.clinica,
            'status': a.status,
            'status_label': ROTULOS_STATUS.get(a.status, a.get_status_display()),
            'observacoes': a.observacoes,
            'feriado': feriado(timezone.localtime(a.data_hora)),
        })
    for c in consultas:
        local = timezone.localtime(c.data_hora)
        if c.agendamento_id or (c.paciente_id, local.date()) in ocupados:
            continue
        itens.append({
            'tipo': 'sessao',
            'id': c.id,
            'data_hora': local,
            'hora_fim': c.hora_fim,
            'paciente': c.paciente,
            'clinica': c.paciente.clinica,
            'status': STATUS_SESSAO,
            'status_label': ROTULOS_STATUS[STATUS_SESSAO],
            'observacoes': '',
            'feriado': feriado(local),
        })
    itens.sort(key=lambda i: (i['data_hora'], i['paciente'].nome))
    return itens


def item_para_json(item):
    return {
        'tipo': item['tipo'],
        'id': item['id'],
        'data': item['data_hora'].strftime('%Y-%m-%d'),
        'hora': item['data_hora'].strftime('%H:%M'),
        'hora_fim': item['hora_fim'].strftime('%H:%M') if item.get('hora_fim') else '',
        'paciente': item['paciente'].nome,
        'paciente_url': reverse('paciente_detail', args=[item['paciente'].id]),
        'clinica': item['clinica'].nome if item['clinica'] else '',
        'status': item['status'],
        'status_label': item['status_label'],
        'feriado': item.get('feriado') or '',
    }
