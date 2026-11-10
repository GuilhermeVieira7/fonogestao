from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('clinica.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    # Em produção apenas as fotos de perfil são servidas por URL direta (somente para usuários logados).
    # Materiais didáticos continuam passando pela view `material_download`, que controla o acesso.
    urlpatterns += [
        re_path(r'^media/(?P<path>perfis/.+)$', login_required(serve), {'document_root': settings.MEDIA_ROOT}),
    ]
