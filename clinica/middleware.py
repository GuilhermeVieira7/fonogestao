from django.shortcuts import redirect
from django.urls import reverse
from django.utils import translation
from .models import TermoVersao, TermoAceite, PerfilUsuario


class PreferenciasUsuarioMiddleware:
    """
    Carrega as preferências do usuário logado (idioma e tema) uma vez por
    requisição e ativa o idioma escolhido para datas, meses e mensagens do sistema.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        perfil = None
        if request.user.is_authenticated:
            perfil = PerfilUsuario.objects.filter(user=request.user).first()
        request.preferencias = perfil
        idioma = perfil.idioma if perfil else None
        if idioma:
            translation.activate(idioma)
            request.LANGUAGE_CODE = translation.get_language()
        response = self.get_response(request)
        if idioma:
            response.headers.setdefault('Content-Language', idioma)
            translation.deactivate()
        return response

EXEMPT_URLS = [
    '/login/',
    '/logout/',
    '/password_reset/',
    '/reset/',
    '/cadastro/',
    '/termos-de-uso/',
    '/politica-de-privacidade/',
    '/aceitar-termos/',
    '/admin/',
    '/static/',
    '/media/',
]


class TermosAceiteMiddleware:
    """Redireciona usuários autenticados que ainda não aceitaram os termos vigentes."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_superuser:
            path = request.path
            if not any(path.startswith(url) for url in EXEMPT_URLS):
                termos_ativos = TermoVersao.objects.filter(ativo=True)
                if termos_ativos.exists():
                    aceitos_ids = TermoAceite.objects.filter(
                        user=request.user
                    ).values_list('termo_id', flat=True)
                    pendentes = termos_ativos.exclude(pk__in=aceitos_ids)
                    if pendentes.exists() and path != reverse('aceitar_termos'):
                        return redirect('aceitar_termos')
        return self.get_response(request)
