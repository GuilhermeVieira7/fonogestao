def preferencias(request):
    """Disponibiliza `prefs` (tema, idioma e foto) para todos os templates."""
    perfil = getattr(request, 'preferencias', None)
    foto_url = ''
    if perfil and perfil.foto:
        try:
            foto_url = perfil.foto.url
        except ValueError:
            foto_url = ''
    return {
        'prefs': {
            'tema': perfil.tema if perfil else 'claro',
            'idioma': perfil.idioma if perfil else 'pt-br',
            'foto_url': foto_url,
        }
    }
