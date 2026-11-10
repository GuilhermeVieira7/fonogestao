from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    HomeView, DashboardFonoView, PacienteDetailView, PacienteUpdateView, AreaPacienteView,
    ExportarProntuarioPDFView, GerarAtividadePDFView, CadastroFonoView, CadastroPacienteView,
    AgendamentoUpdateView, AgendamentoDeleteView,
    ClinicaListView, ClinicaCreateView, ClinicaDetailView, ClinicaUpdateView, ClinicaDeleteView,
    VincularFonoClinicaView, DesvincularFonoClinicaView,
    MaterialDeleteView,
    DisponibilidadeHorariaListView, DisponibilidadeHorariaCreateView, DisponibilidadeHorariaUpdateView, DisponibilidadeHorariaDeleteView,
    AgendamentosPendentesView, ConfirmarAgendamentoView, RejeitarAgendamentoView,
    PacienteAgendamentoCreateView,
    AssistenteView,
    AgendaMensalView, MaterialDownloadView, PerfilView, AlterarSenhaView,
    ConsultaAvaliarView, ConsultaFaltaView, SolicitarRemarcacaoView, ResponderRemarcacaoView,
    TermosUsoView, PoliticaPrivacidadeView, AceitarTermosView,
)

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Recuperação de senha
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),

    # Páginas principais
    path('', HomeView.as_view(), name='home'),
    path('dashboard/', DashboardFonoView.as_view(), name='dashboard_fono'),
    path('paciente/<int:pk>/', PacienteDetailView.as_view(), name='paciente_detail'),
    path('paciente/<int:pk>/editar/', PacienteUpdateView.as_view(), name='paciente_editar'),
    path('paciente/<int:pk>/exportar-pdf/', ExportarProntuarioPDFView.as_view(), name='exportar_pdf'),
    path('paciente/<int:pk>/gerar-atividade/', GerarAtividadePDFView.as_view(), name='gerar_atividade_pdf'),
    path('consulta/<int:pk>/avaliar/', ConsultaAvaliarView.as_view(), name='consulta_avaliar'),
    path('consulta/<int:pk>/falta/', ConsultaFaltaView.as_view(), name='consulta_falta'),
    path('agendamento/<int:pk>/remarcar/', SolicitarRemarcacaoView.as_view(), name='solicitar_remarcacao'),
    path('remarcacao/<int:pk>/responder/', ResponderRemarcacaoView.as_view(), name='responder_remarcacao'),
    path('meus-materiais/', AreaPacienteView.as_view(), name='area_paciente'),
    path('cadastro/fonoaudiologo/', CadastroFonoView.as_view(), name='cadastro_fono'),
    path('cadastro/paciente/', CadastroPacienteView.as_view(), name='cadastro_paciente'),
    path('agendamento/<int:pk>/editar/', AgendamentoUpdateView.as_view(), name='agendamento_editar'),
    path('agendamento/<int:pk>/excluir/', AgendamentoDeleteView.as_view(), name='agendamento_excluir'),

    # Clínicas
    path('clinicas/', ClinicaListView.as_view(), name='clinica_list'),
    path('clinicas/nova/', ClinicaCreateView.as_view(), name='clinica_create'),
    path('clinicas/<int:pk>/', ClinicaDetailView.as_view(), name='clinica_detail'),
    path('clinicas/<int:pk>/editar/', ClinicaUpdateView.as_view(), name='clinica_update'),
    path('clinicas/<int:pk>/excluir/', ClinicaDeleteView.as_view(), name='clinica_delete'),
    path('clinicas/<int:clinica_pk>/vincular/<int:fono_pk>/', VincularFonoClinicaView.as_view(), name='vincular_fono_clinica'),
    path('clinicas/<int:clinica_pk>/desvincular/<int:fono_pk>/', DesvincularFonoClinicaView.as_view(), name='desvincular_fono_clinica'),

    # Materiais Didáticos
    path('material/<int:pk>/excluir/', MaterialDeleteView.as_view(), name='material_delete'),
    path('material/<int:pk>/baixar/', MaterialDownloadView.as_view(), name='material_download'),

    # Agenda personalizada do mês (dados para o calendário)
    path('agenda/mensal/', AgendaMensalView.as_view(), name='agenda_mensal'),

    # Perfil e preferências
    path('perfil/', PerfilView.as_view(), name='perfil'),
    path('perfil/senha/', AlterarSenhaView.as_view(), name='alterar_senha'),

    # Disponibilidades Horárias
    path('disponibilidades/', DisponibilidadeHorariaListView.as_view(), name='disponibilidade_list'),
    path('disponibilidades/nova/', DisponibilidadeHorariaCreateView.as_view(), name='disponibilidade_create'),
    path('disponibilidades/<int:pk>/editar/', DisponibilidadeHorariaUpdateView.as_view(), name='disponibilidade_update'),
    path('disponibilidades/<int:pk>/excluir/', DisponibilidadeHorariaDeleteView.as_view(), name='disponibilidade_delete'),

    # Agendamentos
    path('agendamentos-pendentes/', AgendamentosPendentesView.as_view(), name='agendamentos_pendentes'),
    path('agendamento/<int:pk>/confirmar/', ConfirmarAgendamentoView.as_view(), name='agendamento_confirmar'),
    path('agendamento/<int:pk>/rejeitar/', RejeitarAgendamentoView.as_view(), name='agendamento_rejeitar'),

    # Assistente Inteligente
    path('assistente/', AssistenteView.as_view(), name='assistente'),

    # Termos e Políticas
    path('termos-de-uso/', TermosUsoView.as_view(), name='termos_uso'),
    path('politica-de-privacidade/', PoliticaPrivacidadeView.as_view(), name='politica_privacidade'),
    path('aceitar-termos/', AceitarTermosView.as_view(), name='aceitar_termos'),
]
