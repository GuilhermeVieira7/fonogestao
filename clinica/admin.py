from django.contrib import admin
from .models import Fonoaudiologo, Paciente, MaterialDidatico, Consulta

@admin.register(Fonoaudiologo)
class FonoaudiologoAdmin(admin.ModelAdmin):
    list_display = ('user', 'crfa', 'telefone', 'especialidade')
    search_fields = ('user__first_name', 'user__last_name', 'crfa', 'especialidade')
    list_filter = ('especialidade',)

@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cpf', 'data_nascimento', 'fonoaudiologo', 'user')
    search_fields = ('nome', 'cpf', 'nome_responsavel')
    list_filter = ('fonoaudiologo', 'data_nascimento')

@admin.register(MaterialDidatico)
class MaterialDidaticoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'paciente', 'data_upload')
    search_fields = ('titulo', 'paciente__nome')
    list_filter = ('data_upload', 'paciente__fonoaudiologo')

@admin.register(Consulta)
class ConsultaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'data_hora', 'desempenho_nota')
    search_fields = ('paciente__nome', 'observacoes')
    list_filter = ('data_hora', 'desempenho_nota')
