from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator

class Fonoaudiologo(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='fonoaudiologo')
    crfa = models.CharField('CRFa', max_length=20, unique=True)
    cpf = models.CharField('CPF', max_length=14, unique=True, null=True, blank=True)
    data_nascimento = models.DateField('Data de Nascimento', null=True, blank=True)
    telefone = models.CharField('Telefone', max_length=15)
    especialidade = models.CharField('Especialidade', max_length=100)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Paciente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='paciente_perfil', null=True, blank=True)
    fonoaudiologo = models.ForeignKey(Fonoaudiologo, on_delete=models.CASCADE, related_name='pacientes')
    nome = models.CharField('Nome do Paciente', max_length=255)
    data_nascimento = models.DateField('Data de Nascimento')
    cpf = models.CharField('CPF', max_length=14, unique=True)
    nome_responsavel = models.CharField('Nome do Responsável', max_length=255, blank=True, null=True)
    historico_clinico = models.TextField('Histórico Clínico', blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome


class MaterialDidatico(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='materiais')
    titulo = models.CharField('Título', max_length=200)
    descricao = models.TextField('Descrição', blank=True)
    arquivo = models.FileField(
        upload_to='materiais_didaticos/%Y/%m/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'mp3', 'wav', 'mp4'])],
        blank=True, null=True
    )
    link_externo = models.URLField('Link Externo', blank=True, null=True)
    data_upload = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.titulo} - {self.paciente.nome}"


class Consulta(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='consultas')
    data_hora = models.DateTimeField('Data e Hora da Consulta')
    desempenho_nota = models.IntegerField('Nota de Desempenho (1 a 10)', help_text="Nota de 1 a 10 para o gráfico de evolução")
    observacoes = models.TextField('Observações da Consulta')
    plano_acao = models.TextField('Plano de Ação / Atividades', blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Consulta {self.paciente.nome} - {self.data_hora.strftime('%d/%m/%Y')}"

class Agendamento(models.Model):
    STATUS_CHOICES = [
        ('A', 'Agendado'),
        ('R', 'Realizado'),
        ('C', 'Cancelado'),
    ]
    fonoaudiologo = models.ForeignKey(Fonoaudiologo, on_delete=models.CASCADE, related_name='agendamentos')
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='agendamentos')
    data_hora = models.DateTimeField('Data e Hora')
    status = models.CharField('Status', max_length=1, choices=STATUS_CHOICES, default='A')
    observacoes = models.TextField('Observações', blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.paciente.nome} - {self.data_hora.strftime('%d/%m/%Y %H:%M')}"


