from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator


class Clinica(models.Model):
    ESTADO_CHOICES = [
        ('AC','AC'),('AL','AL'),('AP','AP'),('AM','AM'),('BA','BA'),('CE','CE'),
        ('DF','DF'),('ES','ES'),('GO','GO'),('MA','MA'),('MT','MT'),('MS','MS'),
        ('MG','MG'),('PA','PA'),('PB','PB'),('PR','PR'),('PE','PE'),('PI','PI'),
        ('RJ','RJ'),('RN','RN'),('RS','RS'),('RO','RO'),('RR','RR'),('SC','SC'),
        ('SP','SP'),('SE','SE'),('TO','TO'),
    ]
    nome = models.CharField('Nome da Clínica', max_length=200)
    cnpj = models.CharField('CNPJ', max_length=18, unique=True)
    telefone = models.CharField('Telefone', max_length=15)
    email = models.EmailField('E-mail')
    endereco = models.CharField('Endereço', max_length=255)
    cidade = models.CharField('Cidade', max_length=100)
    estado = models.CharField('Estado', max_length=2, choices=ESTADO_CHOICES)
    cep = models.CharField('CEP', max_length=9)
    ativo = models.BooleanField('Ativa', default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Clínica'
        verbose_name_plural = 'Clínicas'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Fonoaudiologo(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='fonoaudiologo')
    crfa = models.CharField('CRFa', max_length=20, unique=True)
    cpf = models.CharField('CPF', max_length=14, unique=True, null=True, blank=True)
    data_nascimento = models.DateField('Data de Nascimento', null=True, blank=True)
    telefone = models.CharField('Telefone', max_length=15)
    especialidade = models.CharField('Especialidade', max_length=100)
    clinicas = models.ManyToManyField(Clinica, blank=True, related_name='fonoaudiologos', verbose_name='Clínicas')

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    @property
    def whatsapp_url(self):
        if not self.telefone:
            return ""
        import re
        digitos = re.sub(r'\D', '', self.telefone)
        if len(digitos) in [10, 11] and not digitos.startswith('55'):
            digitos = '55' + digitos
        return f"https://wa.me/{digitos}"


class Paciente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='paciente_perfil', null=True, blank=True)
    clinica = models.ForeignKey(Clinica, on_delete=models.SET_NULL, null=True, blank=True, related_name='pacientes', verbose_name='Clínica')
    fonoaudiologo = models.ForeignKey(Fonoaudiologo, on_delete=models.CASCADE, related_name='pacientes', verbose_name='Fonoaudiólogo(a)')
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
    # Texto da atividade quando o material é gerado pelo sistema. Permite
    # regerar o PDF sempre com o modelo institucional mais recente.
    conteudo_atividade = models.TextField('Conteúdo da Atividade', blank=True)
    data_upload = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.titulo} - {self.paciente.nome}"

    @property
    def gerado_pelo_sistema(self):
        return bool(self.conteudo_atividade)

    @property
    def extensao(self):
        if not self.arquivo:
            return ''
        return self.arquivo.name.rsplit('.', 1)[-1].lower() if '.' in self.arquivo.name else ''

    @property
    def tipo_midia(self):
        ext = self.extensao
        if ext in ('mp3', 'wav'):
            return 'audio'
        if ext in ('jpg', 'jpeg', 'png'):
            return 'imagem'
        if ext == 'mp4':
            return 'video'
        if ext == 'pdf' or self.gerado_pelo_sistema:
            return 'documento'
        return ''


class Consulta(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='consultas')
    data_hora = models.DateTimeField('Data e Hora da Consulta')
    desempenho_nota = models.IntegerField('Nota de Desempenho (1 a 10)', help_text="Nota de 1 a 10 para o gráfico de evolução")
    observacoes = models.TextField('Observações da Consulta')
    plano_acao = models.TextField('Plano de Ação / Atividades', blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Consulta {self.paciente.nome} - {self.data_hora.strftime('%d/%m/%Y')}"

    @property
    def desempenho_qualitativo(self):
        if self.desempenho_nota <= 3:
            return 'Em Desenvolvimento'
        elif self.desempenho_nota <= 6:
            return 'Regular'
        elif self.desempenho_nota <= 8:
            return 'Bom'
        else:
            return 'Excelente'

class Agendamento(models.Model):
    STATUS_CHOICES = [
        ('P', 'Pendente de Confirmação'),
        ('A', 'Confirmado'),
        ('R', 'Realizado'),
        ('C', 'Cancelado'),
    ]
    fonoaudiologo = models.ForeignKey(Fonoaudiologo, on_delete=models.CASCADE, related_name='agendamentos')
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='agendamentos_paciente')
    clinica = models.ForeignKey(Clinica, on_delete=models.SET_NULL, null=True, blank=True, related_name='agendamentos', verbose_name='Clínica')
    data_hora = models.DateTimeField('Data e Hora')
    status = models.CharField('Status', max_length=1, choices=STATUS_CHOICES, default='P')
    observacoes = models.TextField('Observações', blank=True)
    motivo_rejeicao = models.TextField('Motivo da Rejeição', blank=True, null=True)
    confirmado_em = models.DateTimeField('Confirmado em', blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.paciente.nome} - {self.data_hora.strftime('%d/%m/%Y %H:%M')}"


class DisponibilidadeHoraria(models.Model):
    DIA_SEMANA_CHOICES = [
        (0, 'Segunda-feira'),
        (1, 'Terça-feira'),
        (2, 'Quarta-feira'),
        (3, 'Quinta-feira'),
        (4, 'Sexta-feira'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]
    
    fonoaudiologo = models.ForeignKey(Fonoaudiologo, on_delete=models.CASCADE, related_name='disponibilidades')
    clinica = models.ForeignKey(Clinica, on_delete=models.CASCADE, related_name='disponibilidades')
    dia_semana = models.IntegerField('Dia da Semana', choices=DIA_SEMANA_CHOICES)
    hora_inicio = models.TimeField('Hora de Início')
    hora_fim = models.TimeField('Hora de Término')
    intervalo_minutos = models.IntegerField('Intervalo entre consultas (minutos)', default=30)
    ativo = models.BooleanField('Ativo', default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Disponibilidade Horária'
        verbose_name_plural = 'Disponibilidades Horárias'
        unique_together = ('fonoaudiologo', 'clinica', 'dia_semana')
        ordering = ['dia_semana', 'hora_inicio']

    def __str__(self):
        return f"{self.fonoaudiologo} - {self.get_dia_semana_display()} {self.hora_inicio.strftime('%H:%M')} às {self.hora_fim.strftime('%H:%M')}"


class TermoVersao(models.Model):
    TIPO_CHOICES = [
        ('uso', 'Termos de Uso'),
        ('privacidade', 'Política de Privacidade'),
        ('lgpd', 'Consentimento LGPD'),
    ]
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES)
    versao = models.CharField('Versão', max_length=20)
    conteudo = models.TextField('Conteúdo')
    ativo = models.BooleanField('Ativo', default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Versão de Termo'
        verbose_name_plural = 'Versões de Termos'
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.get_tipo_display()} v{self.versao}"


class PerfilUsuario(models.Model):
    IDIOMA_CHOICES = [
        ('pt-br', 'Português (Brasil)'),
        ('en', 'English'),
        ('es', 'Español'),
    ]
    TEMA_CHOICES = [
        ('claro', 'Claro'),
        ('escuro', 'Escuro'),
        ('sistema', 'Automático (seguir o sistema)'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    foto = models.ImageField(
        'Foto de Perfil', upload_to='perfis/%Y/%m/', blank=True, null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])],
    )
    idioma = models.CharField('Idioma', max_length=10, choices=IDIOMA_CHOICES, default='pt-br')
    tema = models.CharField('Tema', max_length=10, choices=TEMA_CHOICES, default='claro')
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Perfil de Usuário'
        verbose_name_plural = 'Perfis de Usuário'

    def __str__(self):
        return f"Perfil de {self.user.username}"

    @classmethod
    def para(cls, user):
        """Retorna o perfil do usuário, criando-o com os padrões se ainda não existir."""
        perfil, _ = cls.objects.get_or_create(user=user)
        return perfil


class TermoAceite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='aceites_termos')
    termo = models.ForeignKey(TermoVersao, on_delete=models.CASCADE, related_name='aceites')
    aceito_em = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField('IP do Acesso', null=True, blank=True)

    class Meta:
        verbose_name = 'Aceite de Termo'
        verbose_name_plural = 'Aceites de Termos'
        unique_together = ('user', 'termo')

    def __str__(self):
        return f"{self.user.username} - {self.termo}"

