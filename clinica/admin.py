from django.contrib import admin
from .models import Fonoaudiologo, Paciente, MaterialDidatico, Consulta, Clinica, TermoVersao, TermoAceite, Agendamento, DisponibilidadeHoraria, PerfilUsuario, SolicitacaoRemarcacao

@admin.register(Fonoaudiologo)
class FonoaudiologoAdmin(admin.ModelAdmin):
    list_display = ('user', 'crfa', 'telefone', 'especialidade')
    search_fields = ('user__first_name', 'user__last_name', 'crfa', 'especialidade')
    list_filter = ('especialidade',)
    filter_horizontal = ('clinicas',)

@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cpf', 'clinica', 'fonoaudiologo', 'data_nascimento', 'user')
    search_fields = ('nome', 'cpf', 'nome_responsavel', 'clinica__nome')
    list_filter = ('clinica', 'fonoaudiologo', 'data_nascimento')

@admin.register(MaterialDidatico)
class MaterialDidaticoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'paciente', 'data_upload')
    search_fields = ('titulo', 'paciente__nome')
    list_filter = ('data_upload', 'paciente__fonoaudiologo')

@admin.register(Consulta)
class ConsultaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'data_hora', 'hora_fim', 'avaliada_em')
    search_fields = ('paciente__nome', 'observacoes')
    list_filter = ('data_hora', 'avaliada_em')

@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'fonoaudiologo', 'data_hora', 'hora_fim', 'clinica', 'status', 'criado_em')
    search_fields = ('paciente__nome', 'fonoaudiologo__user__first_name', 'clinica__nome')
    list_filter = ('status', 'data_hora', 'clinica')
    date_hierarchy = 'data_hora'
    readonly_fields = ('criado_em', 'confirmado_em')

@admin.register(DisponibilidadeHoraria)
class DisponibilidadeHorariaAdmin(admin.ModelAdmin):
    list_display = ('fonoaudiologo', 'clinica', 'dia_semana', 'hora_inicio', 'hora_fim', 'intervalo_minutos', 'ativo')
    search_fields = ('fonoaudiologo__user__first_name', 'clinica__nome')
    list_filter = ('dia_semana', 'ativo', 'clinica')
    list_editable = ('ativo',)

@admin.register(Clinica)
class ClinicaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cnpj', 'cidade', 'estado', 'ativo')
    search_fields = ('nome', 'cnpj', 'cidade')
    list_filter = ('estado', 'ativo')
    list_editable = ('ativo',)

@admin.register(TermoVersao)
class TermoVersaoAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'versao', 'ativo', 'criado_em')
    list_filter = ('tipo', 'ativo')
    list_editable = ('ativo',)

@admin.register(TermoAceite)
class TermoAceiteAdmin(admin.ModelAdmin):
    list_display = ('user', 'termo', 'aceito_em', 'ip')
    search_fields = ('user__username', 'user__first_name')
    list_filter = ('termo__tipo', 'aceito_em')
    readonly_fields = ('aceito_em',)


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('user', 'idioma', 'tema', 'atualizado_em')
    list_filter = ('idioma', 'tema')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email')


@admin.register(SolicitacaoRemarcacao)
class SolicitacaoRemarcacaoAdmin(admin.ModelAdmin):
    list_display = ('agendamento', 'data_original', 'nova_data_hora', 'status', 'criado_em', 'respondido_em')
    list_filter = ('status',)
    search_fields = ('agendamento__paciente__nome',)
