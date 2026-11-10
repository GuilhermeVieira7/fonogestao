"""Montagem dos itens exibidos na Agenda do Dia e na Agenda do Mês."""
from django.urls import reverse
from django.utils import timezone

from .models import Agendamento, Consulta

STATUS_SESSAO = 'S'  # sessão registrada no prontuário (modelo Consulta)

ROTULOS_STATUS = {
    'P': 'Pendente',
    'A': 'Confirmado',
    'R': 'Realizado',
    'C': 'Cancelado',
    STATUS_SESSAO: 'Sessão registrada',
}


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
            'paciente': a.paciente,
            'clinica': a.clinica,
            'status': a.status,
            'status_label': ROTULOS_STATUS.get(a.status, a.get_status_display()),
            'observacoes': a.observacoes,
        })
    for c in consultas:
        local = timezone.localtime(c.data_hora)
        if (c.paciente_id, local.date()) in ocupados:
            continue
        itens.append({
            'tipo': 'sessao',
            'id': c.id,
            'data_hora': local,
            'paciente': c.paciente,
            'clinica': c.paciente.clinica,
            'status': STATUS_SESSAO,
            'status_label': ROTULOS_STATUS[STATUS_SESSAO],
            'observacoes': '',
        })
    itens.sort(key=lambda i: (i['data_hora'], i['paciente'].nome))
    return itens


def item_para_json(item):
    return {
        'tipo': item['tipo'],
        'id': item['id'],
        'data': item['data_hora'].strftime('%Y-%m-%d'),
        'hora': item['data_hora'].strftime('%H:%M'),
        'paciente': item['paciente'].nome,
        'paciente_url': reverse('paciente_detail', args=[item['paciente'].id]),
        'clinica': item['clinica'].nome if item['clinica'] else '',
        'status': item['status'],
        'status_label': item['status_label'],
    }
