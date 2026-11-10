"""
Testes de ponta a ponta do FonoGestão: permissões, agenda, PDFs, materiais,
perfil/preferências e validações. Rode com:  python manage.py test clinica
"""
import importlib
import io
import shutil
import tempfile
from datetime import date, datetime, timedelta

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from pypdf import PdfReader

from clinica.models import (Agendamento, Clinica, Consulta, DisponibilidadeHoraria, Fonoaudiologo, MaterialDidatico,
                            Paciente, PerfilUsuario, TermoAceite, TermoVersao)

MEDIA_TESTE = tempfile.mkdtemp(prefix='fonogestao_testes_')


def texto_pdf(conteudo):
    return '\n'.join(p.extract_text() or '' for p in PdfReader(io.BytesIO(conteudo)).pages)


def corpo(response):
    """Conteúdo da resposta, inclusive quando é um FileResponse (streaming)."""
    if getattr(response, 'streaming', False):
        return b''.join(response.streaming_content)
    return response.content


def png_bytes():
    buf = io.BytesIO()
    Image.new('RGB', (40, 40), (0, 121, 107)).save(buf, 'PNG')
    return buf.getvalue()


def local(y, m, d, h=10, mi=0):
    return timezone.make_aware(datetime(y, m, d, h, mi))


@override_settings(MEDIA_ROOT=MEDIA_TESTE)
class BaseSistema(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TESTE, ignore_errors=True)

    def setUp(self):
        self.clinica = Clinica.objects.create(
            nome='Clínica Sonora', cnpj='12.345.678/0001-90', telefone='1133334444', email='c@sonora.com',
            endereco='Av. Paulista, 1000', cidade='São Paulo', estado='SP', cep='01310-100')
        self.u_fono = User.objects.create_user('ana', password='Senha!Forte123', first_name='Ana', last_name='Souza', email='ana@x.com')
        self.fono = Fonoaudiologo.objects.create(user=self.u_fono, crfa='2-111', telefone='11988887777', especialidade='Linguagem')
        self.clinica.fonoaudiologos.add(self.fono)

        self.u_fono2 = User.objects.create_user('beto', password='Senha!Forte123', first_name='Beto')
        self.fono2 = Fonoaudiologo.objects.create(user=self.u_fono2, crfa='2-222', telefone='11977776666', especialidade='Voz')

        self.u_pac = User.objects.create_user('joao', password='Senha!Forte123', first_name='João')
        self.paciente = Paciente.objects.create(
            user=self.u_pac, fonoaudiologo=self.fono, clinica=self.clinica, nome='João da Silva',
            data_nascimento=date(2016, 5, 10), cpf='390.533.447-05', nome_responsavel='Maria da Silva',
            historico_clinico='Trocas fonológicas.')
        self.paciente2 = Paciente.objects.create(
            fonoaudiologo=self.fono2, nome='Pedro Outro', data_nascimento=date(2015, 1, 1), cpf='999.888.777-66')

        self.hoje = timezone.localdate()

    def entrar(self, user):
        self.client.force_login(user)


# ─────────────────────────────────────────────────────────────────────────────
# Acesso e permissões
# ─────────────────────────────────────────────────────────────────────────────

class PermissoesTest(BaseSistema):
    def test_anonimo_e_redirecionado_para_login(self):
        for nome, args in [('dashboard_fono', []), ('agenda_mensal', []), ('perfil', []), ('area_paciente', []),
                           ('paciente_detail', [self.paciente.pk]), ('exportar_pdf', [self.paciente.pk]),
                           ('assistente', []), ('clinica_list', []), ('alterar_senha', [])]:
            r = self.client.get(reverse(nome, args=args))
            self.assertEqual(r.status_code, 302, nome)
            self.assertIn(reverse('login'), r['Location'], nome)

    def test_paciente_nao_acessa_telas_do_fonoaudiologo(self):
        self.entrar(self.u_pac)
        for nome in ['dashboard_fono', 'agenda_mensal', 'assistente', 'clinica_list', 'disponibilidade_list']:
            self.assertEqual(self.client.get(reverse(nome)).status_code, 403, nome)

    def test_fono_nao_acessa_paciente_de_outro_profissional(self):
        self.entrar(self.u_fono)
        self.assertEqual(self.client.get(reverse('paciente_detail', args=[self.paciente2.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('exportar_pdf', args=[self.paciente2.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('gerar_atividade_pdf', args=[self.paciente2.pk])).status_code, 404)

    def test_home_redireciona_por_perfil(self):
        self.entrar(self.u_fono)
        self.assertRedirects(self.client.get(reverse('home')), reverse('dashboard_fono'))
        self.entrar(self.u_pac)
        self.assertRedirects(self.client.get(reverse('home')), reverse('area_paciente'))

    def test_paginas_principais_abrem_sem_erro(self):
        self.entrar(self.u_fono)
        for nome, args in [('dashboard_fono', []), ('assistente', []), ('clinica_list', []), ('clinica_create', []),
                           ('clinica_detail', [self.clinica.pk]), ('disponibilidade_list', []),
                           ('disponibilidade_create', []), ('agendamentos_pendentes', []),
                           ('paciente_detail', [self.paciente.pk]), ('paciente_editar', [self.paciente.pk]),
                           ('gerar_atividade_pdf', [self.paciente.pk]), ('cadastro_paciente', []),
                           ('perfil', []), ('alterar_senha', []), ('termos_uso', []), ('politica_privacidade', [])]:
            self.assertEqual(self.client.get(reverse(nome, args=args)).status_code, 200, nome)
        self.entrar(self.u_pac)
        for nome in ['area_paciente', 'perfil', 'termos_uso']:
            self.assertEqual(self.client.get(reverse(nome)).status_code, 200, nome)

    def test_edicao_mostra_datas_ja_cadastradas(self):
        """Campos <input type=date> precisam vir preenchidos (formato AAAA-MM-DD)."""
        self.entrar(self.u_fono)
        r = self.client.get(reverse('paciente_editar', args=[self.paciente.pk]))
        self.assertContains(r, 'value="2016-05-10"')
        self.fono.data_nascimento = date(1990, 4, 2)
        self.fono.save()
        self.assertContains(self.client.get(reverse('perfil')), 'value="1990-04-02"')


class TermosMiddlewareTest(BaseSistema):
    def test_usuario_com_termo_pendente_e_redirecionado_e_depois_liberado(self):
        TermoVersao.objects.create(tipo='uso', versao='1.0', conteudo='Termos', ativo=True)
        self.entrar(self.u_fono)
        self.assertRedirects(self.client.get(reverse('dashboard_fono')), reverse('aceitar_termos'))
        self.client.post(reverse('aceitar_termos'))
        self.assertTrue(TermoAceite.objects.filter(user=self.u_fono).exists())
        self.assertEqual(self.client.get(reverse('dashboard_fono')).status_code, 200)


# ─────────────────────────────────────────────────────────────────────────────
# Agenda do Dia / Minha Agenda
# ─────────────────────────────────────────────────────────────────────────────

class AgendaDiaTest(BaseSistema):
    def setUp(self):
        super().setUp()
        self.entrar(self.u_fono)
        d = self.hoje
        mk = lambda h, st, pac=None: Agendamento.objects.create(
            fonoaudiologo=self.fono, paciente=pac or self.paciente, clinica=self.clinica,
            data_hora=local(d.year, d.month, d.day, h), status=st)
        self.ag_p, self.ag_a, self.ag_r, self.ag_c = mk(8, 'P'), mk(9, 'A'), mk(10, 'R'), mk(11, 'C')

    def test_agenda_do_dia_mostra_todos_os_status(self):
        r = self.client.get(reverse('dashboard_fono'))
        status = [i['status'] for i in r.context['agendamentos_dia']]
        self.assertEqual(status, ['P', 'A', 'R', 'C'])

    def test_sessao_registrada_no_prontuario_aparece_sem_duplicar(self):
        outro = Paciente.objects.create(fonoaudiologo=self.fono, nome='Ana Clara', data_nascimento=date(2017, 2, 2), cpf='222.333.444-55')
        d = self.hoje
        Consulta.objects.create(paciente=outro, data_hora=local(d.year, d.month, d.day, 15), desempenho_nota=7, observacoes='ok')
        # Mesmo paciente e mesmo dia de um agendamento ativo: não pode duplicar.
        Consulta.objects.create(paciente=self.paciente, data_hora=local(d.year, d.month, d.day, 9, 5), desempenho_nota=6, observacoes='ok')
        itens = self.client.get(reverse('dashboard_fono')).context['agendamentos_dia']
        sessoes = [i for i in itens if i['tipo'] == 'sessao']
        self.assertEqual([s['paciente'].nome for s in sessoes], ['Ana Clara'])
        self.assertEqual(len(itens), 5)

    def test_agendamento_de_outro_profissional_nao_aparece(self):
        Agendamento.objects.create(fonoaudiologo=self.fono2, paciente=self.paciente2, data_hora=local(self.hoje.year, self.hoje.month, self.hoje.day, 12), status='A')
        itens = self.client.get(reverse('dashboard_fono')).context['agendamentos_dia']
        self.assertTrue(all(i['paciente'] != self.paciente2 for i in itens))

    def test_minha_agenda_inclui_pendentes_confirmados_e_realizados(self):
        r = self.client.get(reverse('dashboard_fono'))
        self.assertEqual(set(r.context['agendamentos_confirmados']), {self.ag_p, self.ag_a, self.ag_r})

    def test_navegacao_por_data_e_data_invalida(self):
        amanha = self.hoje + timedelta(days=1)
        r = self.client.get(reverse('dashboard_fono'), {'data': amanha.isoformat()})
        self.assertEqual(r.context['selected_date'], amanha)
        self.assertContains(r, 'Amanhã (')
        self.assertContains(r, 'Voltar para Hoje')
        r = self.client.get(reverse('dashboard_fono'), {'data': 'lixo'})
        self.assertEqual(r.context['selected_date'], self.hoje)
        r = self.client.get(reverse('dashboard_fono'), {'data': '2026-02-30'})
        self.assertEqual(r.status_code, 200)

    def test_botao_hoje_usa_o_mesmo_estilo_translucido_dos_outros_dias(self):
        html = self.client.get(reverse('dashboard_fono')).content.decode()
        trecho = html[html.index('Hoje (') - 400:html.index('Hoje (')]
        self.assertIn('background: var(--surface-2)', trecho)
        self.assertNotIn('linear-gradient', trecho)
        self.assertNotIn('Voltar para Hoje', html)

    def test_icone_da_agenda_abre_o_calendario_do_mes(self):
        r = self.client.get(reverse('dashboard_fono'))
        self.assertContains(r, 'data-bs-target="#agendaMesModal"')
        self.assertContains(r, 'id="agendaMesModal"')

    def test_aba_ativa_respeita_parametro(self):
        r = self.client.get(reverse('dashboard_fono'), {'tab': 'agenda'})
        self.assertEqual(r.context['active_tab'], 'agenda')
        r = self.client.get(reverse('dashboard_fono'), {'tab': '<script>'})
        self.assertEqual(r.context['active_tab'], 'pacientes')


class CriarAgendamentoTest(BaseSistema):
    def setUp(self):
        super().setUp()
        self.entrar(self.u_fono)

    def test_agendamento_criado_pelo_fono_ja_entra_confirmado_e_na_agenda(self):
        quando = (timezone.localtime() + timedelta(days=3)).replace(hour=14, minute=0, second=0, microsecond=0)
        r = self.client.post(reverse('dashboard_fono'), {
            'paciente': self.paciente.pk, 'clinica': self.clinica.pk,
            'data_hora': quando.strftime('%Y-%m-%dT%H:%M'), 'observacoes': ''})
        ag = Agendamento.objects.get()
        self.assertEqual(ag.status, 'A')
        self.assertIsNotNone(ag.confirmado_em)
        self.assertEqual(r.status_code, 302)
        self.assertIn('tab=agenda', r['Location'])
        self.assertIn(f"data={quando:%Y-%m-%d}", r['Location'])
        dia = self.client.get(r['Location']).context['agendamentos_dia']
        self.assertEqual([i['id'] for i in dia], [ag.id])

    def test_nao_agenda_paciente_de_outro_profissional(self):
        r = self.client.post(reverse('dashboard_fono'), {
            'paciente': self.paciente2.pk, 'data_hora': '2030-01-01T10:00'})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Agendamento.objects.exists())
        self.assertTrue(r.context['abrir_modal_agendamento'])
        self.assertIn('paciente', r.context['agendamento_form'].errors)

    def test_formulario_invalido_reabre_o_modal(self):
        r = self.client.post(reverse('dashboard_fono'), {'paciente': self.paciente.pk})
        self.assertContains(r, "getElementById('novoAgendamentoModal')")


class EditarExcluirAgendamentoTest(BaseSistema):
    def setUp(self):
        super().setUp()
        self.entrar(self.u_fono)
        self.ag = Agendamento.objects.create(fonoaudiologo=self.fono, paciente=self.paciente, clinica=self.clinica,
                                             data_hora=local(2030, 5, 20, 14, 30), status='A')
        self.ag_outro = Agendamento.objects.create(fonoaudiologo=self.fono2, paciente=self.paciente2,
                                                   data_hora=local(2030, 5, 20, 15), status='A')

    def test_excluir_volta_para_a_agenda_e_nao_para_a_tela_inicial(self):
        r = self.client.post(reverse('agendamento_excluir', args=[self.ag.pk]))
        self.assertRedirects(r, reverse('dashboard_fono') + '?tab=agenda', fetch_redirect_response=False)
        self.assertFalse(Agendamento.objects.filter(pk=self.ag.pk).exists())

    def test_excluir_respeita_o_dia_que_estava_aberto(self):
        destino = reverse('dashboard_fono') + '?tab=agenda&data=2030-05-20'
        r = self.client.post(reverse('agendamento_excluir', args=[self.ag.pk]) + '?next=' + destino.replace('&', '%26').replace('?', '%3F'))
        self.assertEqual(r['Location'], destino)

    def test_excluir_ignora_redirecionamento_externo(self):
        r = self.client.post(reverse('agendamento_excluir', args=[self.ag.pk]), {'next': 'https://site-malicioso.com/'})
        self.assertEqual(r['Location'], reverse('dashboard_fono') + '?tab=agenda')

    def test_tela_de_confirmacao_tem_voltar_para_a_agenda(self):
        r = self.client.get(reverse('agendamento_excluir', args=[self.ag.pk]))
        self.assertContains(r, 'href="/dashboard/?tab=agenda"')
        self.assertContains(r, 'name="next"')

    def test_nao_exclui_agendamento_de_outro_profissional(self):
        self.assertEqual(self.client.post(reverse('agendamento_excluir', args=[self.ag_outro.pk])).status_code, 404)
        self.assertTrue(Agendamento.objects.filter(pk=self.ag_outro.pk).exists())

    def test_editar_mostra_data_preenchida_e_volta_para_agenda(self):
        r = self.client.get(reverse('agendamento_editar', args=[self.ag.pk]))
        self.assertContains(r, 'value="2030-05-20T14:30"')
        r = self.client.post(reverse('agendamento_editar', args=[self.ag.pk]), {
            'paciente': self.paciente.pk, 'clinica': self.clinica.pk, 'data_hora': '2030-05-21T09:00', 'observacoes': 'x'})
        self.assertEqual(r['Location'], reverse('dashboard_fono') + '?tab=agenda')
        self.ag.refresh_from_db()
        self.assertEqual(timezone.localtime(self.ag.data_hora).day, 21)

    def test_editar_nao_permite_trocar_para_paciente_de_outro(self):
        r = self.client.post(reverse('agendamento_editar', args=[self.ag.pk]), {
            'paciente': self.paciente2.pk, 'data_hora': '2030-05-21T09:00'})
        self.assertEqual(r.status_code, 200)
        self.ag.refresh_from_db()
        self.assertEqual(self.ag.paciente, self.paciente)

    def test_confirmar_e_rejeitar_pendente(self):
        p1 = Agendamento.objects.create(fonoaudiologo=self.fono, paciente=self.paciente, data_hora=local(2030, 6, 1), status='P')
        p2 = Agendamento.objects.create(fonoaudiologo=self.fono, paciente=self.paciente, data_hora=local(2030, 6, 2), status='P')
        self.client.post(reverse('agendamento_confirmar', args=[p1.pk]))
        self.client.post(reverse('agendamento_rejeitar', args=[p2.pk]), {'motivo_rejeicao': 'Sem horário'})
        p1.refresh_from_db(); p2.refresh_from_db()
        self.assertEqual((p1.status, p2.status), ('A', 'C'))
        self.assertIsNotNone(p1.confirmado_em)


# ─────────────────────────────────────────────────────────────────────────────
# Agenda do mês (calendário)
# ─────────────────────────────────────────────────────────────────────────────

class AgendaMensalTest(BaseSistema):
    def setUp(self):
        super().setUp()
        self.entrar(self.u_fono)
        mk = lambda dt, st, fono=None, pac=None: Agendamento.objects.create(
            fonoaudiologo=fono or self.fono, paciente=pac or self.paciente, clinica=self.clinica, data_hora=dt, status=st)
        mk(local(2030, 3, 1, 0, 30), 'A')     # primeiro minuto do mês (fuso local)
        mk(local(2030, 3, 15, 9), 'P')
        mk(local(2030, 3, 31, 23, 30), 'C')   # último dia do mês, tarde da noite
        mk(local(2030, 4, 1, 8), 'A')         # mês seguinte: fora
        mk(local(2030, 3, 10, 9), 'A', fono=self.fono2, pac=self.paciente2)  # outro profissional: fora
        Consulta.objects.create(paciente=self.paciente, data_hora=local(2030, 3, 20, 10), desempenho_nota=8, observacoes='ok')

    def test_retorna_somente_eventos_do_mes_e_do_profissional(self):
        r = self.client.get(reverse('agenda_mensal'), {'ano': 2030, 'mes': 3})
        self.assertEqual(r.status_code, 200)
        dados = r.json()
        self.assertEqual(dados['titulo'], 'Março de 2030')
        self.assertEqual([e['data'] for e in dados['eventos']], ['2030-03-01', '2030-03-15', '2030-03-20', '2030-03-31'])
        self.assertEqual(dados['eventos'][0]['hora'], '00:30')
        self.assertEqual(dados['resumo']['total'], 3)  # cancelado não conta
        self.assertEqual((dados['resumo']['C'], dados['resumo']['S']), (1, 1))
        self.assertTrue(all('Pedro' not in e['paciente'] for e in dados['eventos']))
        self.assertEqual(dados['eventos'][0]['paciente_url'], reverse('paciente_detail', args=[self.paciente.pk]))

    def test_navegacao_entre_anos(self):
        dez = self.client.get(reverse('agenda_mensal'), {'ano': 2030, 'mes': 12}).json()
        self.assertEqual(dez['proximo'], {'ano': 2031, 'mes': 1})
        jan = self.client.get(reverse('agenda_mensal'), {'ano': 2031, 'mes': 1}).json()
        self.assertEqual(jan['anterior'], {'ano': 2030, 'mes': 12})

    def test_sem_parametros_usa_mes_atual(self):
        dados = self.client.get(reverse('agenda_mensal')).json()
        self.assertEqual((dados['ano'], dados['mes']), (self.hoje.year, self.hoje.month))

    def test_parametros_invalidos(self):
        for params in [{'ano': 'x', 'mes': 1}, {'ano': 2030, 'mes': 13}, {'ano': 2030, 'mes': 0}, {'ano': 99999, 'mes': 1}]:
            self.assertEqual(self.client.get(reverse('agenda_mensal'), params).status_code, 400, params)


# ─────────────────────────────────────────────────────────────────────────────
# PDFs e materiais
# ─────────────────────────────────────────────────────────────────────────────

class ProntuarioPDFTest(BaseSistema):
    def setUp(self):
        super().setUp()
        self.entrar(self.u_fono)

    def test_exporta_pdf_institucional_com_dados_e_resumo(self):
        for i, nota in enumerate([3, 5, 8]):
            Consulta.objects.create(paciente=self.paciente, data_hora=local(2026, 3, 1 + i * 7, 14), desempenho_nota=nota,
                                    observacoes=f'Observação {i}', plano_acao='Praticar' if i == 0 else '')
        r = self.client.get(reverse('exportar_pdf', args=[self.paciente.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertTrue(r.content.startswith(b'%PDF'))
        self.assertIn('attachment', r['Content-Disposition'])
        self.assertIn('prontuario_joao-da-silva', r['Content-Disposition'])
        texto = texto_pdf(r.content)
        for esperado in ['Relatório de Evolução Clínica', 'João da Silva', 'Clínica Sonora', 'CRFa', '2-111',
                         'IDENTIFICAÇÃO DO PACIENTE', 'RESUMO DO ACOMPANHAMENTO', 'Melhora', 'Observação 2',
                         'Documento confidencial', 'PRT-']:
            self.assertIn(esperado, texto, esperado)
        self.assertLess(texto.index('Observação 0'), texto.index('Observação 2'))  # ordem cronológica

    def test_exporta_sem_consultas_e_sem_clinica(self):
        sem = Paciente.objects.create(fonoaudiologo=self.fono, nome='Sem Dados', data_nascimento=date(2020, 1, 1), cpf='555.555.555-55')
        r = self.client.get(reverse('exportar_pdf', args=[sem.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertIn('Nenhuma sessão registrada', texto_pdf(r.content))


class AtividadeEMateriaisTest(BaseSistema):
    def gerar(self, titulo='Treino do R', conteudo='Repita "rato" 10 vezes.\nUse o espelho.'):
        self.entrar(self.u_fono)
        return self.client.post(reverse('gerar_atividade_pdf', args=[self.paciente.pk]),
                                {'titulo': titulo, 'conteudo_atividade': conteudo})

    def test_gerar_atividade_salva_conteudo_e_volta_para_aba_materiais(self):
        r = self.gerar()
        self.assertEqual(r['Location'], reverse('paciente_detail', args=[self.paciente.pk]) + '?tab=materiais')
        m = MaterialDidatico.objects.get()
        self.assertEqual(m.conteudo_atividade, 'Repita "rato" 10 vezes.\nUse o espelho.')
        self.assertTrue(m.arquivo.name.endswith('.pdf'))
        self.assertTrue(m.arquivo.name.isascii())

    def test_paciente_baixa_atividade_no_modelo_institucional(self):
        self.gerar()
        m = MaterialDidatico.objects.get()
        self.entrar(self.u_pac)
        area = self.client.get(reverse('area_paciente'))
        self.assertContains(area, reverse('material_download', args=[m.pk]))
        r = self.client.get(reverse('material_download', args=[m.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertIn('attachment', r['Content-Disposition'])
        texto = texto_pdf(r.content)
        for esperado in ['ATIVIDADE PARA CASA', 'Treino do R', 'João da Silva', 'ORIENTAÇÕES', 'Repita',
                         'REGISTRO SEMANAL', 'Ana Souza', 'CRFa', 'Clínica Sonora']:
            self.assertIn(esperado, texto, esperado)

    def test_atividade_antiga_sem_conteudo_serve_o_arquivo_original(self):
        m = MaterialDidatico.objects.create(paciente=self.paciente, titulo='Antigo',
                                            arquivo=SimpleUploadedFile('antigo.pdf', b'%PDF-1.4 original'))
        self.entrar(self.u_pac)
        r = self.client.get(reverse('material_download', args=[m.pk]))
        self.assertEqual(corpo(r), b'%PDF-1.4 original')

    def test_outros_usuarios_nao_baixam_o_material(self):
        self.gerar()
        m = MaterialDidatico.objects.get()
        self.entrar(self.u_fono2)
        self.assertEqual(self.client.get(reverse('material_download', args=[m.pk])).status_code, 404)
        outro_user = User.objects.create_user('outro', password='x')
        Paciente.objects.create(user=outro_user, fonoaudiologo=self.fono, nome='Outro', data_nascimento=date(2010, 1, 1), cpf='123.123.123-12')
        self.entrar(outro_user)
        self.assertEqual(self.client.get(reverse('material_download', args=[m.pk])).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('material_download', args=[m.pk])).status_code, 302)

    def test_material_somente_com_link_nao_quebra_as_telas(self):
        MaterialDidatico.objects.create(paciente=self.paciente, titulo='Vídeo', link_externo='https://example.com/v')
        self.entrar(self.u_fono)
        self.assertContains(self.client.get(reverse('paciente_detail', args=[self.paciente.pk])), 'https://example.com/v')
        self.entrar(self.u_pac)
        self.assertContains(self.client.get(reverse('area_paciente')), 'https://example.com/v')

    def test_upload_exige_arquivo_ou_link(self):
        self.entrar(self.u_fono)
        r = self.client.post(reverse('paciente_detail', args=[self.paciente.pk]), {'material_upload': '1', 'titulo': 'Vazio'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['abrir_modal'], 'uploadMaterialModal')
        self.assertFalse(MaterialDidatico.objects.exists())

    def test_upload_de_imagem_aparece_para_o_paciente(self):
        self.entrar(self.u_fono)
        self.client.post(reverse('paciente_detail', args=[self.paciente.pk]), {
            'material_upload': '1', 'titulo': 'Figura', 'arquivo': SimpleUploadedFile('fig.png', png_bytes(), 'image/png')})
        m = MaterialDidatico.objects.get()
        self.assertEqual(m.tipo_midia, 'imagem')
        self.entrar(self.u_pac)
        r = self.client.get(reverse('material_download', args=[m.pk]) + '?inline=1')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('attachment', r['Content-Disposition'])

    def test_excluir_material_volta_para_aba_materiais(self):
        m = MaterialDidatico.objects.create(paciente=self.paciente, titulo='X', link_externo='https://example.com')
        self.entrar(self.u_fono)
        r = self.client.post(reverse('material_delete', args=[m.pk]))
        self.assertEqual(r['Location'], reverse('paciente_detail', args=[self.paciente.pk]) + '?tab=materiais')

    def test_extrator_da_migracao_recupera_texto_de_pdf_antigo(self):
        mod = importlib.import_module('clinica.migrations.0011_recuperar_conteudo_atividades')
        texto = ('Atividade Personalizada gerada via FonoGestão\n FonoGestão - Atividades\nNome: X\n'
                 'Instruções do(a) Fonoaudiólogo(a):\nPratique o alfabeto em\nambiente domiciliar\n')
        self.assertEqual(mod.extrair_conteudo(texto), 'Pratique o alfabeto em ambiente domiciliar')
        self.assertEqual(mod.extrair_conteudo('sem marcador'), '')


# ─────────────────────────────────────────────────────────────────────────────
# Consultas, disponibilidades e cadastros (validações que antes davam erro 500)
# ─────────────────────────────────────────────────────────────────────────────

class ValidacoesTest(BaseSistema):
    def test_nota_de_consulta_deve_estar_entre_1_e_10(self):
        self.entrar(self.u_fono)
        url = reverse('paciente_detail', args=[self.paciente.pk])
        r = self.client.post(url, {'data_hora': '2026-03-01T10:00', 'desempenho_nota': 15, 'observacoes': 'x'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['abrir_modal'], 'novaConsultaModal')
        self.assertFalse(Consulta.objects.exists())
        r = self.client.post(url, {'data_hora': '2026-03-01T10:00', 'desempenho_nota': 7, 'observacoes': 'x'})
        self.assertEqual(r['Location'], url + '?tab=consultas')

    def test_disponibilidade_duplicada_mostra_erro_em_vez_de_quebrar(self):
        self.entrar(self.u_fono)
        dados = {'clinica': self.clinica.pk, 'dia_semana': 0, 'hora_inicio': '08:00', 'hora_fim': '12:00', 'intervalo_minutos': 30, 'ativo': 'on'}
        self.assertEqual(self.client.post(reverse('disponibilidade_create'), dados).status_code, 302)
        r = self.client.post(reverse('disponibilidade_create'), dados)
        self.assertEqual(r.status_code, 200)
        self.assertIn('dia_semana', r.context['form'].errors)
        self.assertEqual(DisponibilidadeHoraria.objects.count(), 1)

    def test_disponibilidade_com_horario_final_antes_do_inicial(self):
        self.entrar(self.u_fono)
        r = self.client.post(reverse('disponibilidade_create'), {
            'clinica': self.clinica.pk, 'dia_semana': 1, 'hora_inicio': '12:00', 'hora_fim': '08:00', 'intervalo_minutos': 30})
        self.assertIn('hora_fim', r.context['form'].errors)

    def test_editar_disponibilidade_nao_conflita_consigo_mesma(self):
        self.entrar(self.u_fono)
        d = DisponibilidadeHoraria.objects.create(fonoaudiologo=self.fono, clinica=self.clinica, dia_semana=2,
                                                  hora_inicio='08:00', hora_fim='12:00')
        r = self.client.post(reverse('disponibilidade_update', args=[d.pk]), {
            'clinica': self.clinica.pk, 'dia_semana': 2, 'hora_inicio': '09:00', 'hora_fim': '12:00', 'intervalo_minutos': 30, 'ativo': 'on'})
        self.assertEqual(r.status_code, 302)

    def test_cadastro_com_usuario_existente_mostra_erro(self):
        r = self.client.post(reverse('cadastro_fono'), {
            'username': 'ANA', 'password': 'x', 'first_name': 'Outra', 'email': 'o@x.com',
            'crfa': '9-999', 'telefone': '1', 'especialidade': 'Voz'})
        self.assertEqual(r.status_code, 200)
        self.assertIn('username', r.context['form'].errors)
        r = self.client.post(reverse('cadastro_paciente'), {
            'username': 'joao', 'password': 'x', 'nome': 'X', 'data_nascimento': '2010-01-01', 'cpf': '000.000.000-00',
            'clinica': self.clinica.pk, 'fonoaudiologo': self.fono.pk})
        self.assertIn('username', r.context['form'].errors)

    def test_fono_cadastra_paciente_com_acesso(self):
        self.entrar(self.u_fono)
        r = self.client.post(reverse('cadastro_paciente'), {
            'clinica': self.clinica.pk, 'nome': 'Novo Paciente', 'data_nascimento': '2019-01-01', 'cpf': '529.982.247-25',
            'criar_acesso': 'on', 'username': 'novo', 'password': 'Senha!Forte123'})
        novo = Paciente.objects.get(nome='Novo Paciente')
        self.assertRedirects(r, reverse('paciente_detail', args=[novo.pk]))
        self.assertEqual(novo.user.username, 'novo')


class CPFTest(BaseSistema):
    def test_digitos_verificadores(self):
        from clinica.forms import cpf_valido
        for valido in ['52998224725', '12345678909', '39053344705']:
            self.assertTrue(cpf_valido(valido), valido)
        for invalido in ['52998224724', '11111111111', '00000000000', '1234567890', '123456789012', 'abcdefghijk']:
            self.assertFalse(cpf_valido(invalido), invalido)

    def novo_paciente(self, cpf, nome='Paciente CPF'):
        return self.client.post(reverse('cadastro_paciente'), {
            'clinica': self.clinica.pk, 'nome': nome, 'data_nascimento': '2019-01-01', 'cpf': cpf})

    def test_cpf_invalido_e_recusado_com_mensagem(self):
        self.entrar(self.u_fono)
        for cpf, msg in [('111.222.333-44', 'CPF inválido'), ('111.111.111-11', 'CPF inválido'),
                         ('123.456', 'O CPF deve ter 11 dígitos'), ('', 'Este campo é obrigatório')]:
            r = self.novo_paciente(cpf)
            self.assertEqual(r.status_code, 200, cpf)
            self.assertIn('cpf', r.context['form'].errors, cpf)
            self.assertContains(r, msg)
        self.assertFalse(Paciente.objects.filter(nome='Paciente CPF').exists())

    def test_cpf_so_com_numeros_e_gravado_formatado(self):
        self.entrar(self.u_fono)
        r = self.novo_paciente('52998224725')
        novo = Paciente.objects.get(nome='Paciente CPF')
        self.assertRedirects(r, reverse('paciente_detail', args=[novo.pk]))
        self.assertEqual(novo.cpf, '529.982.247-25')

    def test_cpf_duplicado_mesmo_em_formato_diferente(self):
        self.entrar(self.u_fono)
        r = self.novo_paciente('39053344705')  # mesmo CPF do paciente base, sem pontuação
        self.assertContains(r, 'Já existe um cadastro com este CPF')
        Paciente.objects.filter(pk=self.paciente2.pk).update(cpf='12345678909')  # registro antigo sem pontuação
        r = self.novo_paciente('123.456.789-09')
        self.assertContains(r, 'Já existe um cadastro com este CPF')

    def test_edicao_mantem_o_proprio_cpf_e_valida_alteracao(self):
        self.entrar(self.u_fono)
        url = reverse('paciente_editar', args=[self.paciente.pk])
        dados = {'clinica': self.clinica.pk, 'nome': 'João da Silva', 'data_nascimento': '2016-05-10',
                 'cpf': '390.533.447-05', 'nome_responsavel': 'Maria da Silva', 'historico_clinico': 'x'}
        self.assertEqual(self.client.post(url, dados).status_code, 302)
        r = self.client.post(url, {**dados, 'cpf': '390.533.447-06'})
        self.assertContains(r, 'CPF inválido')
        self.paciente.refresh_from_db()
        self.assertEqual(self.paciente.cpf, '390.533.447-05')

    def test_cadastro_de_fono_cpf_opcional_mas_validado(self):
        base = {'password': 'Senha!Forte123', 'first_name': 'Fono Novo', 'email': 'f@x.com',
                'telefone': '11', 'especialidade': 'Voz'}
        r = self.client.post(reverse('cadastro_fono'), {**base, 'username': 'f1', 'crfa': '7-001', 'cpf': '123.456.789-00'})
        self.assertIn('cpf', r.context['form'].errors)
        self.client.post(reverse('cadastro_fono'), {**base, 'username': 'f2', 'crfa': '7-002', 'cpf': ''})
        self.client.post(reverse('cadastro_fono'), {**base, 'username': 'f3', 'crfa': '7-003', 'cpf': ''})
        self.assertEqual(Fonoaudiologo.objects.filter(crfa__in=['7-002', '7-003'], cpf__isnull=True).count(), 2)


class NomeDoSistemaTest(BaseSistema):
    def test_nome_fonogestao_acentuado(self):
        r = self.client.get(reverse('password_reset'))
        self.assertContains(r, 'FonoGestão')
        self.assertNotContains(r, 'FonoGestao')
        self.entrar(self.u_fono)
        for nome, args in [('dashboard_fono', []), ('clinica_list', []), ('clinica_detail', [self.clinica.pk]),
                           ('termos_uso', []), ('politica_privacidade', [])]:
            self.assertNotContains(self.client.get(reverse(nome, args=args)), 'FonoGestao', msg_prefix=nome)


# ─────────────────────────────────────────────────────────────────────────────
# Perfil e preferências
# ─────────────────────────────────────────────────────────────────────────────

class PerfilTest(BaseSistema):
    def dados(self, **extra):
        base = {'dados-first_name': 'Ana Paula', 'dados-last_name': 'Souza', 'dados-email': 'ana.paula@x.com',
                'extra-telefone': '11911112222', 'extra-especialidade': 'Motricidade Orofacial', 'extra-data_nascimento': '1990-04-02',
                'pref-idioma': 'pt-br', 'pref-tema': 'claro'}
        base.update(extra)
        return base

    def test_clicar_no_perfil_da_barra_lateral_leva_as_configuracoes(self):
        self.entrar(self.u_fono)
        self.assertContains(self.client.get(reverse('dashboard_fono')), f'href="{reverse("perfil")}" class="sidebar-user-link"')

    def test_fono_atualiza_nome_dados_e_preferencias(self):
        self.entrar(self.u_fono)
        r = self.client.post(reverse('perfil'), self.dados(**{'pref-tema': 'escuro', 'pref-idioma': 'es'}))
        self.assertRedirects(r, reverse('perfil'))
        self.u_fono.refresh_from_db(); self.fono.refresh_from_db()
        perfil = PerfilUsuario.objects.get(user=self.u_fono)
        self.assertEqual(self.u_fono.get_full_name(), 'Ana Paula Souza')
        self.assertEqual(self.u_fono.email, 'ana.paula@x.com')
        self.assertEqual(self.fono.especialidade, 'Motricidade Orofacial')
        self.assertEqual((perfil.tema, perfil.idioma), ('escuro', 'es'))

    def test_tema_e_idioma_sao_aplicados_nas_paginas(self):
        self.entrar(self.u_fono)
        self.client.post(reverse('perfil'), self.dados(**{'pref-tema': 'escuro', 'pref-idioma': 'en'}))
        r = self.client.get(reverse('dashboard_fono'))
        self.assertContains(r, '<html lang="en" data-tema="escuro">')
        self.assertEqual(r['Content-Language'], 'en')
        self.client.post(reverse('perfil'), self.dados(**{'pref-tema': 'sistema'}))
        self.assertContains(self.client.get(reverse('dashboard_fono')), 'data-tema="sistema"')

    def test_idioma_traduz_mensagens_do_sistema(self):
        self.entrar(self.u_fono)
        self.client.post(reverse('perfil'), self.dados(**{'pref-idioma': 'en'}))
        r = self.client.post(reverse('perfil'), self.dados(**{'pref-idioma': 'en', 'dados-email': 'nao-e-email'}))
        self.assertContains(r, 'Enter a valid email address.')

    def test_upload_e_remocao_de_foto(self):
        self.entrar(self.u_fono)
        foto = SimpleUploadedFile('eu.png', png_bytes(), 'image/png')
        self.client.post(reverse('perfil'), self.dados(**{'pref-foto': foto}))
        perfil = PerfilUsuario.objects.get(user=self.u_fono)
        self.assertTrue(perfil.foto)
        self.assertContains(self.client.get(reverse('dashboard_fono')), perfil.foto.url)
        self.client.post(reverse('perfil'), self.dados(**{'pref-remover_foto': 'on'}))
        perfil.refresh_from_db()
        self.assertFalse(perfil.foto)

    def test_foto_invalida_e_rejeitada(self):
        self.entrar(self.u_fono)
        r = self.client.post(reverse('perfil'), self.dados(**{'pref-foto': SimpleUploadedFile('x.png', b'nao e imagem', 'image/png')}))
        self.assertEqual(r.status_code, 200)
        self.assertIn('foto', r.context['preferencias_form'].errors)

    def test_email_duplicado_e_nome_vazio_sao_rejeitados(self):
        User.objects.create_user('z', email='ocupado@x.com', password='x')
        self.entrar(self.u_fono)
        r = self.client.post(reverse('perfil'), self.dados(**{'dados-email': 'OCUPADO@x.com', 'dados-first_name': ''}))
        self.assertIn('email', r.context['dados_form'].errors)
        self.assertIn('first_name', r.context['dados_form'].errors)
        self.u_fono.refresh_from_db()
        self.assertEqual(self.u_fono.first_name, 'Ana')

    def test_paciente_e_superusuario_tambem_tem_perfil(self):
        self.entrar(self.u_pac)
        r = self.client.post(reverse('perfil'), {'dados-first_name': 'Joãozinho', 'dados-last_name': '', 'dados-email': '',
                                                 'extra-nome_responsavel': 'Carlos', 'pref-idioma': 'pt-br', 'pref-tema': 'escuro'})
        self.assertEqual(r.status_code, 302)
        self.paciente.refresh_from_db()
        self.assertEqual(self.paciente.nome_responsavel, 'Carlos')
        admin = User.objects.create_superuser('root', 'r@x.com', 'x')
        self.entrar(admin)
        self.assertEqual(self.client.get(reverse('perfil')).status_code, 200)

    def test_alterar_senha(self):
        self.entrar(self.u_fono)
        r = self.client.post(reverse('alterar_senha'), {'old_password': 'Senha!Forte123',
                                                        'new_password1': 'NovaSenha!2026x', 'new_password2': 'NovaSenha!2026x'})
        self.assertRedirects(r, reverse('perfil'))
        self.u_fono.refresh_from_db()
        self.assertTrue(self.u_fono.check_password('NovaSenha!2026x'))
        r = self.client.post(reverse('alterar_senha'), {'old_password': 'errada', 'new_password1': 'a', 'new_password2': 'b'})
        self.assertEqual(r.status_code, 200)
