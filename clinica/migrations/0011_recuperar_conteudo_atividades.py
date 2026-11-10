"""
Recupera o texto das atividades geradas antes da existência do campo
`conteudo_atividade`, lendo o PDF antigo. Assim essas atividades também
passam a ser baixadas com o novo modelo institucional.

Falhas de leitura são ignoradas: o material continua servindo o PDF original.
"""
import re

from django.db import migrations

DESCRICAO_GERADA = 'Gerado automaticamente via sistema.'
MARCADOR = 'Fonoaudiólogo(a):'


def extrair_conteudo(texto):
    if MARCADOR not in texto:
        return ''
    trecho = texto.split(MARCADOR, 1)[1].strip()
    # O PDF antigo quebrava linhas longas: junta as quebras simples em espaço.
    paragrafos = re.split(r'\n\s*\n', trecho)
    return '\n\n'.join(' '.join(l.strip() for l in p.splitlines() if l.strip()) for p in paragrafos).strip()


def recuperar(apps, schema_editor):
    MaterialDidatico = apps.get_model('clinica', 'MaterialDidatico')
    try:
        from pypdf import PdfReader
    except ImportError:
        return
    for material in MaterialDidatico.objects.filter(descricao=DESCRICAO_GERADA, conteudo_atividade=''):
        if not material.arquivo:
            continue
        try:
            with material.arquivo.open('rb') as fh:
                texto = '\n'.join(p.extract_text() or '' for p in PdfReader(fh).pages)
        except Exception:
            continue
        conteudo = extrair_conteudo(texto)
        if conteudo:
            material.conteudo_atividade = conteudo
            material.save(update_fields=['conteudo_atividade'])


class Migration(migrations.Migration):

    dependencies = [
        ('clinica', '0010_perfil_usuario_e_conteudo_atividade'),
    ]

    operations = [
        migrations.RunPython(recuperar, migrations.RunPython.noop),
    ]
