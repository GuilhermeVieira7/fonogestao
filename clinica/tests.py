from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from clinica.models import Clinica, Fonoaudiologo, Paciente
from clinica.forms import PacienteCadastroForm


class ClinicaAcessoEMedicoTestCase(TestCase):
    def setUp(self):
        # Médico 1
        self.user_fono1 = User.objects.create_user(username='dr_alfa', password='123', first_name='Dr. Alfa')
        self.fono1 = Fonoaudiologo.objects.create(
            user=self.user_fono1, crfa='11111', telefone='11999990001', especialidade='Voz'
        )

        # Médico 2
        self.user_fono2 = User.objects.create_user(username='dr_beta', password='123', first_name='Dr. Beta')
        self.fono2 = Fonoaudiologo.objects.create(
            user=self.user_fono2, crfa='22222', telefone='11999990002', especialidade='Audiologia'
        )

        # Clínica A (onde apenas fono1 está cadastrado)
        self.clinica_a = Clinica.objects.create(
            nome='Clínica Alfa Saúde', cnpj='11.111.111/0001-11', telefone='1133330001',
            email='alfa@clinica.com', endereco='Rua A, 100', cidade='São Paulo', estado='SP', cep='01001-000'
        )
        self.clinica_a.fonoaudiologos.add(self.fono1)

        # Clínica B (onde apenas fono2 está cadastrado)
        self.clinica_b = Clinica.objects.create(
            nome='Clínica Beta Audição', cnpj='22.222.222/0001-22', telefone='1133330002',
            email='beta@clinica.com', endereco='Rua B, 200', cidade='São Paulo', estado='SP', cep='02002-000'
        )
        self.clinica_b.fonoaudiologos.add(self.fono2)

        self.client1 = Client()
        self.client1.login(username='dr_alfa', password='123')

        self.client2 = Client()
        self.client2.login(username='dr_beta', password='123')

    def test_medico_so_enxerga_suas_clinicas_na_lista(self):
        # Médico 1 acessa lista de clínicas
        response = self.client1.get(reverse('clinica_list'))
        self.assertEqual(response.status_code, 200)
        clinicas_listadas = list(response.context['clinicas'])
        self.assertIn(self.clinica_a, clinicas_listadas)
        self.assertNotIn(self.clinica_b, clinicas_listadas)

        # Médico 2 acessa lista de clínicas
        response = self.client2.get(reverse('clinica_list'))
        self.assertEqual(response.status_code, 200)
        clinicas_listadas = list(response.context['clinicas'])
        self.assertIn(self.clinica_b, clinicas_listadas)
        self.assertNotIn(self.clinica_a, clinicas_listadas)

    def test_medico_nao_cadastrado_nao_pode_acessar_clinica(self):
        # Médico 1 tenta acessar Clínica B (na qual NÃO está cadastrado)
        response = self.client1.get(reverse('clinica_detail', kwargs={'pk': self.clinica_b.pk}))
        self.assertEqual(response.status_code, 404)

        # Médico 2 tenta acessar Clínica A (na qual NÃO está cadastrado)
        response = self.client2.get(reverse('clinica_detail', kwargs={'pk': self.clinica_a.pk}))
        self.assertEqual(response.status_code, 404)

        # Médico 1 acessa Clínica A (onde ESTÁ cadastrado)
        response = self.client1.get(reverse('clinica_detail', kwargs={'pk': self.clinica_a.pk}))
        self.assertEqual(response.status_code, 200)

    def test_criacao_de_clinica_vincula_automaticamente_o_medico(self):
        dados_clinica = {
            'nome': 'Nova Clínica Gama',
            'cnpj': '33.333.333/0001-33',
            'telefone': '1133330003',
            'email': 'gama@clinica.com',
            'endereco': 'Rua G, 300',
            'cidade': 'São Paulo',
            'estado': 'SP',
            'cep': '03003-000',
            'ativo': True
        }
        response = self.client1.post(reverse('clinica_create'), data=dados_clinica)
        self.assertEqual(response.status_code, 302)
        nova_clinica = Clinica.objects.get(cnpj='33.333.333/0001-33')
        self.assertIn(self.fono1, nova_clinica.fonoaudiologos.all())

    def test_paciente_deve_estar_vinculado_a_clinica_e_medico_cadastrado(self):
        # Caso INVÁLIDO: paciente tenta vincular fono2 (que NÃO está na clinica_a)
        form_invalido = PacienteCadastroForm(data={
            'username': 'paciente_invalido',
            'password': 'senha123456',
            'nome': 'Paciente Teste Inválido',
            'data_nascimento': '2010-01-01',
            'cpf': '123.456.789-01',
            'clinica': self.clinica_a.id,
            'fonoaudiologo': self.fono2.id, # fono2 não está na clinica_a!
        })
        self.assertFalse(form_invalido.is_valid())
        self.assertIn('fonoaudiologo', form_invalido.errors)

        # Caso VÁLIDO: paciente vincula fono1 (que está na clinica_a)
        form_valido = PacienteCadastroForm(data={
            'username': 'paciente_valido',
            'password': 'senha123456',
            'nome': 'Paciente Teste Válido',
            'data_nascimento': '2010-01-01',
            'cpf': '987.654.321-09',
            'clinica': self.clinica_a.id,
            'fonoaudiologo': self.fono1.id,
        })
        self.assertTrue(form_valido.is_valid(), form_valido.errors)
        paciente = form_valido.save()
        self.assertEqual(paciente.clinica, self.clinica_a)
        self.assertEqual(paciente.fonoaudiologo, self.fono1)
