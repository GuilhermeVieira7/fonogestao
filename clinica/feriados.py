"""
Feriados nacionais do Brasil (fixos e móveis), calculados sem depender de
serviços externos. Feriados estaduais e municipais não estão incluídos.
"""
from datetime import date, timedelta
from functools import lru_cache

FIXOS = {
    (1, 1): 'Confraternização Universal',
    (4, 21): 'Tiradentes',
    (5, 1): 'Dia do Trabalho',
    (9, 7): 'Independência do Brasil',
    (10, 12): 'Nossa Senhora Aparecida',
    (11, 2): 'Finados',
    (11, 15): 'Proclamação da República',
    (11, 20): 'Dia da Consciência Negra',
    (12, 25): 'Natal',
}


def pascoa(ano):
    """Domingo de Páscoa (algoritmo de Meeus/Jones/Butcher)."""
    a = ano % 19
    b, c = divmod(ano, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(ano, mes, dia)


@lru_cache(maxsize=64)
def feriados_do_ano(ano):
    """Dicionário {data: nome} com os feriados (e pontos facultativos nacionais) do ano."""
    feriados = {date(ano, m, d): nome for (m, d), nome in FIXOS.items()}
    if ano < 2024:
        feriados.pop(date(ano, 11, 20), None)  # nacional a partir de 2024 (Lei 14.759/2023)
    p = pascoa(ano)
    feriados[p - timedelta(days=48)] = 'Carnaval'
    feriados[p - timedelta(days=47)] = 'Carnaval'
    feriados[p - timedelta(days=2)] = 'Sexta-feira Santa'
    feriados[p + timedelta(days=60)] = 'Corpus Christi'
    return feriados


def feriado(dia):
    """Nome do feriado na data (date ou datetime), ou None."""
    if hasattr(dia, 'date'):
        dia = dia.date()
    return feriados_do_ano(dia.year).get(dia)
