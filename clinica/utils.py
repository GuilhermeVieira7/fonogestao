import os
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa

def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html  = template.render(context_dict)
    response = HttpResponse(content_type='application/pdf')
    # Use Content-Disposition: attachment; filename="pdf.pdf" para forçar download
    # response['Content-Disposition'] = 'attachment; filename="relatorio.pdf"'
    
    # Criar o PDF
    pisa_status = pisa.CreatePDF(
       html, dest=response)
    
    # Se houver erro, retorna string de erro
    if pisa_status.err:
       return HttpResponse('Encontramos alguns erros <pre>' + html + '</pre>')
    return response
