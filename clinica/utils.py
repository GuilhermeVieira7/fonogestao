import logging
import os
from io import BytesIO

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import get_template
from django.utils import timezone
from django.utils.http import content_disposition_header
from django.utils.text import slugify
from xhtml2pdf import pisa

logger = logging.getLogger(__name__)

LOGO_PATH = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo_fonogestao.svg')


def _link_callback(uri, rel):
    """Converte URLs de static/media em caminhos do disco para o xhtml2pdf."""
    if uri.startswith(settings.MEDIA_URL) or uri.startswith('/' + settings.MEDIA_URL):
        caminho = os.path.join(settings.MEDIA_ROOT, uri.split(settings.MEDIA_URL, 1)[1])
    elif uri.startswith(settings.STATIC_URL) or uri.startswith('/' + settings.STATIC_URL):
        caminho = os.path.join(settings.BASE_DIR, 'static', uri.split(settings.STATIC_URL, 1)[1])
    else:
        return uri
    return caminho if os.path.isfile(caminho) else uri


def gerar_pdf_bytes(template_src, context_dict=None):
    """Renderiza um template em PDF e devolve os bytes, ou None em caso de erro."""
    contexto = {
        'logo_path': LOGO_PATH.replace(os.sep, '/'),
        'emitido_em': timezone.localtime(),
    }
    contexto.update(context_dict or {})
    html = get_template(template_src).render(contexto)
    buffer = BytesIO()
    resultado = pisa.CreatePDF(html, dest=buffer, encoding='utf-8', link_callback=_link_callback)
    if resultado.err:
        logger.error('Falha ao gerar PDF a partir de %s', template_src)
        return None
    return buffer.getvalue()


def render_to_pdf(template_src, context_dict=None):
    """Compatibilidade: devolve um HttpResponse com o PDF, ou None em caso de erro."""
    pdf = gerar_pdf_bytes(template_src, context_dict)
    if pdf is None:
        return None
    return HttpResponse(pdf, content_type='application/pdf')


def nome_arquivo_seguro(*partes, extensao='pdf'):
    """Gera um nome de arquivo sem acentos/espaços (ex.: 'relatorio_joaozinho-silva.pdf')."""
    base = '_'.join(slugify(str(p)) for p in partes if p) or 'documento'
    return f'{base}.{extensao}'


def resposta_pdf(pdf_bytes, filename, inline=False):
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = content_disposition_header(not inline, filename)
    return response
