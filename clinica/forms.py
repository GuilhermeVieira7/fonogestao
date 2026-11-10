from django import forms
from django.contrib.auth.models import User
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

class ConsultaForm(forms.ModelForm):
    class Meta:
        model = Consulta
        fields = ['data_hora', 'desempenho_nota', 'observacoes', 'plano_acao']
        widgets = {
            'data_hora': datetime_local_widget(),
            'desempenho_nota': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_desempenho_nota(self):
        nota = self.cleaned_data.get('desempenho_nota')
        if nota is not None and not 1 <= nota <= 10:
            raise forms.ValidationError('A nota de desempenho deve estar entre 1 e 10.')
        return nota

class AgendamentoForm(forms.ModelForm):
    class Meta:
        model = Agendamento
        fields = ['paciente', 'clinica', 'data_hora', 'observacoes']
        widgets = {
            'paciente': forms.Select(attrs={'class': 'form-control'}),
            'clinica': forms.Select(attrs={'class': 'form-control'}),
            'data_hora': datetime_local_widget(),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        fonoaudiologo = kwargs.pop('fonoaudiologo', None)
        super().__init__(*args, **kwargs)
        self.fields['clinica'].required = False
        if fonoaudiologo is not None:
            # O profissional só pode agendar seus próprios pacientes e clínicas.
            self.fields['paciente'].queryset = Paciente.objects.filter(fonoaudiologo=fonoaudiologo)
            self.fields['clinica'].queryset = fonoaudiologo.clinicas.filter(ativo=True)

class GerarAtividadeForm(forms.Form):
    titulo = forms.CharField(max_length=200, label="Título da Atividade", widget=forms.TextInput(attrs={'class': 'form-control'}))
    conteudo_atividade = forms.CharField(label="Instruções para a Casa", widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}))

class MaterialUploadForm(forms.ModelForm):
    class Meta:
        model = MaterialDidatico
        fields = ['titulo', 'descricao', 'arquivo', 'link_externo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'arquivo': forms.FileInput(attrs={'class': 'form-control'}),
            'link_externo': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('arquivo') and not cleaned_data.get('link_externo') and not self.errors:
            raise forms.ValidationError('Envie um arquivo ou informe um link externo.')
        return cleaned_data

class FonoaudiologoCadastroForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True, label="Nome de Usuário (Login)", widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Senha", required=True)
    first_name = forms.CharField(max_length=150, required=True, label="Nome Completo", widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Fonoaudiologo
        fields = ['crfa', 'cpf', 'data_nascimento', 'telefone', 'especialidade']
        widgets = {
            'crfa': forms.TextInput(attrs={'class': 'form-control'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apenas números'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'especialidade': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_username(self):
        return validar_username_disponivel(self.cleaned_data.get('username'))

class PacienteCadastroForm(forms.ModelForm):
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
            'cpf': forms.TextInput(attrs={'class': 'form-control'}),
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


class FonoCadastraPacienteForm(forms.ModelForm):
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
            'cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000.000.000-00'}),
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


class PacienteUpdateForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = ['clinica', 'nome', 'data_nascimento', 'cpf', 'nome_responsavel', 'historico_clinico']
        widgets = {
            'clinica': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'cpf': forms.TextInput(attrs={'class': 'form-control'}),
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
