from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    HomeView, DashboardFonoView, PacienteDetailView, AreaPacienteView,
    ExportarProntuarioPDFView, GerarAtividadePDFView, CadastroFonoView, CadastroPacienteView,
    AgendamentoUpdateView, AgendamentoDeleteView
)

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # Recuperação de senha
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
    
    path('', HomeView.as_view(), name='home'),
    path('dashboard/', DashboardFonoView.as_view(), name='dashboard_fono'),
    path('paciente/<int:pk>/', PacienteDetailView.as_view(), name='paciente_detail'),
    path('paciente/<int:pk>/exportar-pdf/', ExportarProntuarioPDFView.as_view(), name='exportar_pdf'),
    path('paciente/<int:pk>/gerar-atividade/', GerarAtividadePDFView.as_view(), name='gerar_atividade_pdf'),
    path('meus-materiais/', AreaPacienteView.as_view(), name='area_paciente'),
    path('cadastro/fonoaudiologo/', CadastroFonoView.as_view(), name='cadastro_fono'),
    path('cadastro/paciente/', CadastroPacienteView.as_view(), name='cadastro_paciente'),
    path('agendamento/<int:pk>/editar/', AgendamentoUpdateView.as_view(), name='agendamento_editar'),
    path('agendamento/<int:pk>/excluir/', AgendamentoDeleteView.as_view(), name='agendamento_excluir'),
]
