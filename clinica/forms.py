from django import forms
from django.contrib.auth.models import User
import calendar
from datetime import date, datetime, timedelta

from django.utils import timezone
from .models import Consulta, Agendamento, Fonoaudiologo, Paciente, MaterialDidatico, Clinica, DisponibilidadeHoraria, PerfilUsuario

# Formato aceito pelo <input type="datetime-local">. Sem ele, ao editar um
# registro o campo de data aparece vazio no navegador.
DATETIME_LOCAL_FORMAT = '%Y-%m-%dT%H:%M'


def datetime_local_widget():
    return forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}, format=DATETIME_LOCAL_FORMAT)


def validar_username_disponivel(username):
    if username and User.objects.filter(username__iexact=username).exists():
        raise forms.ValidationError('Este nome de usuário já está em uso. Escolha outro.')
    return username


def cpf_valido(digitos):
    """Confere os dois dígitos verificadores de um CPF (11 dígitos, só números)."""
    if len(digitos) != 11 or not digitos.isdigit() or digitos == digitos[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(d) * peso for d, peso in zip(digitos[:tamanho], range(tamanho + 1, 1, -1)))
        digito = (soma * 10) % 11 % 10
        if digito != int(digitos[tamanho]):
            return False
    return True


def formatar_cpf(digitos):
    return f'{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}'


class CPFValidoMixin:
    """Valida o CPF (dígitos verificadores), grava no formato 000.000.000-00
    e impede duplicidade mesmo que o registro antigo esteja salvo sem pontuação."""

    cpf_obrigatorio = True

    def clean_cpf(self):
        valor = (self.cleaned_data.get('cpf') or '').strip()
        if not valor:
            if self.cpf_obrigatorio:
                raise forms.ValidationError('Informe o CPF.')
            return None
        digitos = ''.join(c for c in valor if c.isdigit())
        if len(digitos) != 11:
            raise forms.ValidationError('O CPF deve ter 11 dígitos.')
        if not cpf_valido(digitos):
            raise forms.ValidationError('CPF inválido. Confira os números digitados.')
        cpf = formatar_cpf(digitos)
        existentes = self._meta.model.objects.filter(cpf__in=[cpf, digitos])
        if self.instance.pk:
            existentes = existentes.exclude(pk=self.instance.pk)
        if existentes.exists():
            raise forms.ValidationError('Já existe um cadastro com este CPF.')
        return cpf


class ClinicaForm(forms.ModelForm):
    class Meta:
        model = Clinica
        fields = ['nome', 'cnpj', 'telefone', 'email', 'endereco', 'cidade', 'estado', 'cep', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da clínica'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0000-00'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Rua, nº, complemento'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'cep': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00000-000'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input', 'type': 'checkbox'}),
        }
        labels = {
            'nome': 'Nome da Clínica',
            'cnpj': 'CNPJ',
            'telefone': 'Telefone',
            'email': 'E-mail',
            'endereco': 'Endereço',
            'cidade': 'Cidade',
            'estado': 'Estado',
            'cep': 'CEP',
            'ativo': 'Ativa',
        }

def time_widget():
    return forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}, format='%H:%M')


def validar_horario_termino(form, campo_inicio='data_hora', campo_fim='hora_fim'):
    """O término precisa ser depois do início (no mesmo dia)."""
    inicio = form.cleaned_data.get(campo_inicio)
    fim = form.cleaned_data.get(campo_fim)
    if inicio and fim and fim <= timezone.localtime(inicio).time():
        form.add_error(campo_fim, 'O horário de término deve ser depois do horário de início.')


class ConsultaForm(forms.ModelForm):
    """Registro manual de uma sessão (sem agendamento). Já entra avaliada."""

    class Meta:
        model = Consulta
        fields = ['data_hora', 'hora_fim', 'observacoes', 'plano_acao']
        widgets = {
            'data_hora': datetime_local_widget(),
            'hora_fim': time_widget(),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'plano_acao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'data_hora': 'Data e horário de início',
            'hora_fim': 'Horário de término',
            'observacoes': 'Observações da sessão',
            'plano_acao': 'Plano de ação / atividades',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['observacoes'].required = True

    def clean(self):
        cleaned_data = super().clean()
        validar_horario_termino(self)
        return cleaned_data


class AvaliacaoConsultaForm(forms.ModelForm):
    """Avaliação qualitativa de uma sessão que já aconteceu."""

    class Meta:
        model = Consulta
        fields = ['observacoes', 'plano_acao']
        widgets = {
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 5,
                                                 'placeholder': 'Como foi a sessão, o que foi trabalhado, evolução observada...'}),
            'plano_acao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                                'placeholder': 'Atividades e orientações para as próximas sessões e para casa'}),
        }
        labels = {
            'observacoes': 'Observações da sessão',
            'plano_acao': 'Plano de ação / atividades',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['observacoes'].required = True


def somar_periodo(dia, quantidade, unidade):
    """Data final de um período a partir de `dia` (dias, meses ou anos)."""
    if unidade == 'dias':
        return dia + timedelta(days=quantidade)
    meses = quantidade * (12 if unidade == 'anos' else 1)
    total = dia.month - 1 + meses
    ano, mes = dia.year + total // 12, total % 12 + 1
    return dia.replace(year=ano, month=mes, day=min(dia.day, calendar.monthrange(ano, mes)[1]))


class AgendamentoForm(forms.ModelForm):
    PERIODO_MAXIMO_DIAS = 731  # até 2 anos de sessões recorrentes
    TIPO_CHOICES = [('unica', 'Consulta única'), ('recorrente', 'Consultas recorrentes')]
    UNIDADE_CHOICES = [('dias', 'Dias'), ('meses', 'Meses'), ('anos', 'Anos')]

    tipo_agendamento = forms.ChoiceField(
        required=False, choices=TIPO_CHOICES, initial='unica', label='Tipo de agendamento',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}))
    periodo_quantidade = forms.IntegerField(
        required=False, min_value=1, initial=3, label='Duração do período',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}))
    periodo_unidade = forms.ChoiceField(
        required=False, choices=UNIDADE_CHOICES, initial='meses', label='Unidade',
        widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = Agendamento
        fields = ['paciente', 'clinica', 'data_hora', 'hora_fim', 'observacoes']
        widgets = {
            'paciente': forms.Select(attrs={'class': 'form-control'}),
            'clinica': forms.Select(attrs={'class': 'form-control'}),
            'data_hora': datetime_local_widget(),
            'hora_fim': time_widget(),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'data_hora': 'Data e horário de início',
            'hora_fim': 'Horário de término',
        }

    def __init__(self, *args, **kwargs):
        fonoaudiologo = kwargs.pop('fonoaudiologo', None)
        super().__init__(*args, **kwargs)
        self.fields['clinica'].required = False
        self.fields['hora_fim'].required = True
        if fonoaudiologo is not None:
            # O profissional só pode agendar seus próprios pacientes e clínicas.
            self.fields['paciente'].queryset = Paciente.objects.filter(fonoaudiologo=fonoaudiologo)
            self.fields['clinica'].queryset = fonoaudiologo.clinicas.filter(ativo=True)
        if self.instance.pk:
            # A recorrência só existe ao criar; ao editar, altera-se uma sessão por vez.
            for campo in ('tipo_agendamento', 'periodo_quantidade', 'periodo_unidade'):
                del self.fields[campo]

    @property
    def recorrente(self):
        return self.cleaned_data.get('tipo_agendamento') == 'recorrente'

    def clean(self):
        cleaned_data = super().clean()
        validar_horario_termino(self)
        if self.recorrente:
            qtd = cleaned_data.get('periodo_quantidade')
            unidade = cleaned_data.get('periodo_unidade')
            if not qtd:
                self.add_error('periodo_quantidade', 'Informe a duração do período das consultas recorrentes.')
            if not unidade:
                self.add_error('periodo_unidade', 'Escolha dias, meses ou anos.')
            inicio = cleaned_data.get('data_hora')
            if qtd and unidade and inicio:
                dia = timezone.localtime(inicio).date()
                try:
                    fim = somar_periodo(dia, qtd, unidade)
                except (OverflowError, ValueError):
                    fim = date.max
                if (fim - dia).days > self.PERIODO_MAXIMO_DIAS:
                    self.add_error('periodo_quantidade', 'O período máximo de consultas recorrentes é de 2 anos.')
        return cleaned_data

    def datas_das_sessoes(self):
        """
        Datas/horários de início das sessões a criar. Na consulta recorrente,
        repete toda semana (mesmo dia da semana e horário da primeira) até o fim do período.
        """
        primeira = timezone.localtime(self.cleaned_data['data_hora']).replace(tzinfo=None)
        if not self.recorrente:
            return [timezone.make_aware(primeira)]
        limite = somar_periodo(primeira.date(), self.cleaned_data['periodo_quantidade'],
                               self.cleaned_data['periodo_unidade'])
        datas, atual = [], primeira
        while atual.date() < limite or not datas:
            datas.append(timezone.make_aware(atual))
            atual += timedelta(weeks=1)
        return datas


class SolicitacaoRemarcacaoForm(forms.Form):
    """Paciente/responsável pede para mover a sessão para outro dia da mesma semana."""
    nova_data = forms.DateField(label='Novo dia', widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'},
                                                                          format='%Y-%m-%d'))
    hora_inicio = forms.TimeField(label='Início', widget=time_widget())
    hora_fim = forms.TimeField(label='Término', widget=time_widget())
    motivo = forms.CharField(label='Mensagem para o(a) profissional', required=False, max_length=500,
                             widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2,
                                                          'placeholder': 'Ex.: prefiro no período da tarde'}))

    def __init__(self, *args, agendamento=None, **kwargs):
        self.agendamento = agendamento
        inicio = timezone.localtime(agendamento.data_hora)
        self.semana_inicio = inicio.date() - timedelta(days=inicio.weekday())
        self.semana_fim = self.semana_inicio + timedelta(days=6)
        kwargs.setdefault('initial', {
            'hora_inicio': inicio.time().replace(second=0, microsecond=0),
            'hora_fim': agendamento.fim.time(),
        })
        super().__init__(*args, **kwargs)
        self.fields['nova_data'].widget.attrs.update({'min': self.semana_inicio.isoformat(),
                                                      'max': self.semana_fim.isoformat()})

    def clean(self):
        from .feriados import feriado
        cleaned_data = super().clean()
        dia, ini, fim = cleaned_data.get('nova_data'), cleaned_data.get('hora_inicio'), cleaned_data.get('hora_fim')
        if dia:
            original = timezone.localtime(self.agendamento.data_hora).date()
            if not self.semana_inicio <= dia <= self.semana_fim:
                self.add_error('nova_data', f'Escolha um dia da mesma semana da sessão '
                                            f'({self.semana_inicio:%d/%m} a {self.semana_fim:%d/%m}).')
            elif dia == original:
                self.add_error('nova_data', 'Escolha um dia diferente do dia original da sessão.')
            elif feriado(dia):
                self.add_error('nova_data', f'{dia:%d/%m} também é feriado ({feriado(dia)}). Escolha outro dia.')
            elif dia.weekday() == 6:
                self.add_error('nova_data', 'Escolha um dia entre segunda-feira e sábado.')
        if ini and fim and fim <= ini:
            self.add_error('hora_fim', 'O horário de término deve ser depois do horário de início.')
        if dia and ini and not self.errors:
            quando = timezone.make_aware(datetime.combine(dia, ini))
            if quando <= timezone.now():
                self.add_error('nova_data', 'Escolha um dia e horário que ainda não passaram.')
            cleaned_data['nova_data_hora'] = quando
        return cleaned_data


class GerarAtividadeForm(forms.Form):
    titulo = forms.CharField(max_length=200, label="Título da Atividade", widget=forms.TextInput(attrs={'class': 'form-control'}))
    conteudo_atividade = forms.CharField(label="Instruções para a Casa", widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}))

class MaterialUploadForm(forms.ModelForm):
    TAMANHO_MAXIMO_MB = 25

    class Meta:
        model = MaterialDidatico
        fields = ['titulo', 'descricao', 'arquivo', 'link_externo', 'visivel_paciente']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'arquivo': forms.FileInput(attrs={'class': 'form-control',
                                              'accept': '.pdf,.jpg,.jpeg,.png,.mp3,.wav,.mp4,application/pdf'}),
            'link_externo': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'visivel_paciente': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'arquivo': 'Arquivo (PDF, imagem, áudio ou vídeo)',
            'visivel_paciente': 'Disponibilizar para o paciente na área dele',
        }
        help_texts = {
            'visivel_paciente': 'Desmarque para guardar documentos internos (laudos, exames, relatórios) só no prontuário.',
        }

    def clean_arquivo(self):
        arquivo = self.cleaned_data.get('arquivo')
        if arquivo and getattr(arquivo, 'size', 0) > self.TAMANHO_MAXIMO_MB * 1024 * 1024:
            raise forms.ValidationError(f'O arquivo deve ter no máximo {self.TAMANHO_MAXIMO_MB} MB.')
        return arquivo

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('arquivo') and not cleaned_data.get('link_externo') and not self.errors:
            raise forms.ValidationError('Envie um arquivo ou informe um link externo.')
        return cleaned_data

class FonoaudiologoCadastroForm(CPFValidoMixin, forms.ModelForm):
    cpf_obrigatorio = False
    username = forms.CharField(max_length=150, required=True, label="Nome de Usuário (Login)", widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Senha", required=True)
    first_name = forms.CharField(max_length=150, required=True, label="Nome Completo", widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Fonoaudiologo
        fields = ['crfa', 'cpf', 'data_nascimento', 'telefone', 'especialidade']
        widgets = {
            'crfa': forms.TextInput(attrs={'class': 'form-control'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000.000.000-00', 'inputmode': 'numeric'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'especialidade': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_username(self):
        return validar_username_disponivel(self.cleaned_data.get('username'))

class PacienteCadastroForm(CPFValidoMixin, forms.ModelForm):
    username = forms.CharField(max_length=150, required=True, label="Nome de Usuário (Login)", widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Senha", required=True)
    
    class Meta:
        model = Paciente
        fields = ['clinica', 'fonoaudiologo', 'nome', 'data_nascimento', 'cpf', 'nome_responsavel', 'historico_clinico']
        widgets = {
            'clinica': forms.Select(attrs={'class': 'form-select'}),
            'fonoaudiologo': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000.000.000-00', 'inputmode': 'numeric'}),
            'nome_responsavel': forms.TextInput(attrs={'class': 'form-control'}),
            'historico_clinico': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'clinica': 'Clínica',
            'fonoaudiologo': 'Fonoaudiólogo(a) / Profissional',
            'nome': 'Nome do Paciente',
            'data_nascimento': 'Data de Nascimento',
            'cpf': 'CPF',
            'nome_responsavel': 'Nome do Responsável',
            'historico_clinico': 'Histórico Clínico',
        }

    def clean_username(self):
        return validar_username_disponivel(self.cleaned_data.get('username'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['clinica'].required = True
        self.fields['clinica'].queryset = Clinica.objects.filter(ativo=True)
        self.fields['clinica'].empty_label = "Selecione a clínica"
        self.fields['fonoaudiologo'].required = True
        self.fields['fonoaudiologo'].empty_label = "Selecione o profissional"

    def clean(self):
        cleaned_data = super().clean()
        clinica = cleaned_data.get('clinica')
        fono = cleaned_data.get('fonoaudiologo')
        if clinica and fono:
            if not clinica.fonoaudiologos.filter(pk=fono.pk).exists():
                self.add_error('fonoaudiologo', f'O(A) profissional {fono} não está cadastrado(a) na clínica {clinica.nome}.')
        return cleaned_data


class FonoCadastraPacienteForm(CPFValidoMixin, forms.ModelForm):
    criar_acesso = forms.BooleanField(
        required=False,
        initial=True,
        label="Criar conta de acesso para o paciente acessar o portal",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'criarAcessoCheck', 'onchange': 'toggleAcessoFields()'})
    )
    username = forms.CharField(
        max_length=150,
        required=False,
        label="Nome de Usuário (Login do Paciente)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: joaosilva', 'id': 'id_username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Senha de acesso', 'id': 'id_password'}),
        label="Senha de Acesso",
        required=False
    )

    class Meta:
        model = Paciente
        fields = ['clinica', 'nome', 'data_nascimento', 'cpf', 'nome_responsavel', 'historico_clinico']
        widgets = {
            'clinica': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome completo do paciente'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000.000.000-00', 'inputmode': 'numeric'}),
            'nome_responsavel': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do responsável (opcional)'}),
            'historico_clinico': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Queixa principal, diagnóstico ou observações iniciais...'}),
        }
        labels = {
            'clinica': 'Clínica de Atendimento',
            'nome': 'Nome Completo do Paciente',
            'data_nascimento': 'Data de Nascimento',
            'cpf': 'CPF do Paciente ou Responsável',
            'nome_responsavel': 'Nome do Responsável',
            'historico_clinico': 'Histórico Clínico / Queixa Inicial',
        }

    def __init__(self, *args, **kwargs):
        self.fonoaudiologo = kwargs.pop('fonoaudiologo', None)
        super().__init__(*args, **kwargs)
        self.fields['clinica'].required = True
        self.fields['clinica'].empty_label = "Selecione a clínica"
        if self.fonoaudiologo:
            self.fields['clinica'].queryset = self.fonoaudiologo.clinicas.filter(ativo=True)
        else:
            self.fields['clinica'].queryset = Clinica.objects.filter(ativo=True)

    def clean(self):
        cleaned_data = super().clean()
        criar_acesso = cleaned_data.get('criar_acesso')
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if criar_acesso:
            if not username:
                self.add_error('username', 'Informe o nome de usuário para o acesso do paciente.')
            elif User.objects.filter(username__iexact=username).exists():
                self.add_error('username', 'Este nome de usuário já está cadastrado no sistema.')
            if not password:
                self.add_error('password', 'Defina uma senha de acesso para o paciente.')

        return cleaned_data


class PacienteUpdateForm(CPFValidoMixin, forms.ModelForm):
    class Meta:
        model = Paciente
        fields = ['clinica', 'nome', 'data_nascimento', 'cpf', 'nome_responsavel', 'historico_clinico']
        widgets = {
            'clinica': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000.000.000-00', 'inputmode': 'numeric'}),
            'nome_responsavel': forms.TextInput(attrs={'class': 'form-control'}),
            'historico_clinico': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'clinica': 'Clínica',
            'nome': 'Nome do Paciente',
            'data_nascimento': 'Data de Nascimento',
            'cpf': 'CPF',
            'nome_responsavel': 'Nome do Responsável',
            'historico_clinico': 'Histórico Clínico',
        }

    def __init__(self, *args, **kwargs):
        fono = kwargs.pop('fonoaudiologo', None)
        super().__init__(*args, **kwargs)
        self.fields['clinica'].required = True
        if fono:
            self.fields['clinica'].queryset = fono.clinicas.filter(ativo=True)
        else:
            self.fields['clinica'].queryset = Clinica.objects.filter(ativo=True)
        self.fields['clinica'].empty_label = "Selecione a clínica"

class PacienteAgendamentoForm(forms.ModelForm):
    class Meta:
        model = Agendamento
        fields = ['clinica', 'data_hora', 'observacoes']
        widgets = {
            'clinica': forms.Select(attrs={'class': 'form-control form-select'}),
            'data_hora': datetime_local_widget(),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Ex: Queixa ou observações sobre a consulta'}),
        }
        labels = {
            'clinica': 'Clínica',
            'data_hora': 'Data e Hora da Consulta',
            'observacoes': 'Observações (Opcional)',
        }
    
    def __init__(self, *args, **kwargs):
        # Recebe o fonoaudiologo como argumento
        fonoaudiologo = kwargs.pop('fonoaudiologo', None)
        super().__init__(*args, **kwargs)
        
        # Se houver fonoaudiólogo, filtra as clínicas associadas a ele
        if fonoaudiologo:
            # Tenta filtrar pelas clínicas do fonoaudiólogo
            clinicas_queryset = fonoaudiologo.clinicas.filter(ativo=True)
            # Se não houver clínicas associadas, mostra TODAS as clínicas ativas
            if not clinicas_queryset.exists():
                clinicas_queryset = Clinica.objects.filter(ativo=True)
            self.fields['clinica'].queryset = clinicas_queryset
        else:
            # Se não tiver fonoaudiólogo, mostra todas as clínicas ativas
            self.fields['clinica'].queryset = Clinica.objects.filter(ativo=True)
        
        # Adiciona empty label
        self.fields['clinica'].empty_label = "Selecione uma clínica"
        self.fields['data_hora'].required = True

    def clean_data_hora(self):
        data_hora = self.cleaned_data.get('data_hora')
        if data_hora and data_hora < timezone.now():
            raise forms.ValidationError('Escolha uma data e hora futuras para a consulta.')
        return data_hora

class DisponibilidadeHorariaForm(forms.ModelForm):
    class Meta:
        model = DisponibilidadeHoraria
        fields = ['clinica', 'dia_semana', 'hora_inicio', 'hora_fim', 'intervalo_minutos', 'ativo']
        widgets = {
            'clinica': forms.Select(attrs={'class': 'form-control'}),
            'dia_semana': forms.Select(attrs={'class': 'form-control'}),
            'hora_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'hora_fim': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'intervalo_minutos': forms.NumberInput(attrs={'class': 'form-control', 'min': 15, 'step': 15}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'clinica': 'Clínica',
            'dia_semana': 'Dia da Semana',
            'hora_inicio': 'Hora de Início',
            'hora_fim': 'Hora de Término',
            'intervalo_minutos': 'Intervalo entre Consultas (minutos)',
            'ativo': 'Ativo',
        }

    def __init__(self, *args, **kwargs):
        self.fonoaudiologo = kwargs.pop('fonoaudiologo', None)
        super().__init__(*args, **kwargs)
        if self.fonoaudiologo is not None:
            self.fields['clinica'].queryset = self.fonoaudiologo.clinicas.filter(ativo=True)

    def clean(self):
        cleaned_data = super().clean()
        inicio, fim = cleaned_data.get('hora_inicio'), cleaned_data.get('hora_fim')
        if inicio and fim and fim <= inicio:
            self.add_error('hora_fim', 'O horário de término deve ser depois do horário de início.')
        intervalo = cleaned_data.get('intervalo_minutos')
        if intervalo is not None and intervalo <= 0:
            self.add_error('intervalo_minutos', 'O intervalo deve ser maior que zero.')
        # unique_together inclui o fonoaudiólogo, que não está no formulário;
        # sem esta checagem um horário duplicado gerava erro 500 no banco.
        clinica, dia = cleaned_data.get('clinica'), cleaned_data.get('dia_semana')
        if self.fonoaudiologo is not None and clinica and dia is not None:
            duplicado = DisponibilidadeHoraria.objects.filter(
                fonoaudiologo=self.fonoaudiologo, clinica=clinica, dia_semana=dia
            ).exclude(pk=self.instance.pk)
            if duplicado.exists():
                self.add_error('dia_semana', 'Você já possui um horário cadastrado para este dia nesta clínica. Edite o existente.')
        return cleaned_data

class ConfirmarAgendamentoForm(forms.ModelForm):
    class Meta:
        model = Agendamento
        fields = []

class RejeitarAgendamentoForm(forms.ModelForm):
    class Meta:
        model = Agendamento
        fields = ['motivo_rejeicao']
        widgets = {
            'motivo_rejeicao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Explique o motivo da rejeição'}),
        }
        labels = {
            'motivo_rejeicao': 'Motivo da Rejeição',
        }


# ─────────────────────────────────────────────────────────────────────────────
# Perfil e preferências
# ─────────────────────────────────────────────────────────────────────────────

class UsuarioDadosForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Seu nome'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Seu sobrenome'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'voce@exemplo.com'}),
        }
        labels = {'first_name': 'Nome', 'last_name': 'Sobrenome', 'email': 'E-mail'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Este e-mail já está sendo usado por outra conta.')
        return email


class FonoaudiologoPerfilForm(forms.ModelForm):
    class Meta:
        model = Fonoaudiologo
        fields = ['telefone', 'especialidade', 'data_nascimento']
        widgets = {
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 00000-0000'}),
            'especialidade': forms.TextInput(attrs={'class': 'form-control'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
        }


class PacientePerfilForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = ['nome_responsavel']
        widgets = {
            'nome_responsavel': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do responsável (opcional)'}),
        }
        labels = {'nome_responsavel': 'Nome do Responsável'}


class PerfilPreferenciasForm(forms.ModelForm):
    TAMANHO_MAXIMO_FOTO = 5 * 1024 * 1024

    remover_foto = forms.BooleanField(required=False, label='Remover foto atual')

    class Meta:
        model = PerfilUsuario
        fields = ['foto', 'idioma', 'tema']
        widgets = {
            'foto': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/png,image/jpeg,image/webp'}),
            'idioma': forms.Select(attrs={'class': 'form-select'}),
            'tema': forms.RadioSelect(),
        }

    def clean_foto(self):
        foto = self.cleaned_data.get('foto')
        if foto and hasattr(foto, 'size') and foto.size > self.TAMANHO_MAXIMO_FOTO:
            raise forms.ValidationError('A foto deve ter no máximo 5 MB.')
        return foto

    def save(self, commit=True):
        perfil = super().save(commit=False)
        nova_foto = 'foto' in self.changed_data and self.cleaned_data.get('foto')
        if self.cleaned_data.get('remover_foto') and not nova_foto:
            if perfil.foto:
                perfil.foto.delete(save=False)
            perfil.foto = None
        if commit:
            perfil.save()
        return perfil
