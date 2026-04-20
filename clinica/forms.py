from django import forms
from django.contrib.auth.models import User
from .models import Consulta, Agendamento, Fonoaudiologo, Paciente, MaterialDidatico

class ConsultaForm(forms.ModelForm):
    class Meta:
        model = Consulta
        fields = ['data_hora', 'desempenho_nota', 'observacoes', 'plano_acao']
        widgets = {
            'data_hora': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'desempenho_nota': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class AgendamentoForm(forms.ModelForm):
    class Meta:
        model = Agendamento
        fields = ['paciente', 'data_hora', 'observacoes']
        widgets = {
            'paciente': forms.Select(attrs={'class': 'form-control'}),
            'data_hora': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

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
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'especialidade': forms.TextInput(attrs={'class': 'form-control'}),
        }

class PacienteCadastroForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True, label="Nome de Usuário (Login)", widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Senha", required=True)
    
    class Meta:
        model = Paciente
        fields = ['fonoaudiologo', 'nome', 'data_nascimento', 'cpf', 'nome_responsavel', 'historico_clinico']
        widgets = {
            'fonoaudiologo': forms.Select(attrs={'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control'}),
            'nome_responsavel': forms.TextInput(attrs={'class': 'form-control'}),
            'historico_clinico': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
