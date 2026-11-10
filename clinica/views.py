import calendar
import os
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView, View

from .agenda import item_para_json, itens_agenda
from .forms import (AgendamentoForm, ClinicaForm, ConfirmarAgendamentoForm, ConsultaForm, DisponibilidadeHorariaForm,
                    FonoaudiologoCadastroForm, FonoaudiologoPerfilForm, FonoCadastraPacienteForm, GerarAtividadeForm,
                    MaterialUploadForm, PacienteAgendamentoForm, PacienteCadastroForm, PacientePerfilForm,
                    PacienteUpdateForm, PerfilPreferenciasForm, RejeitarAgendamentoForm, UsuarioDadosForm)
from .models import (Agendamento, Clinica, Consulta, DisponibilidadeHoraria, Fonoaudiologo, MaterialDidatico, Paciente,
                     PerfilUsuario, TermoAceite, TermoVersao)
from .utils import gerar_pdf_bytes, nome_arquivo_seguro, resposta_pdf

MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho',
         'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']


class FonoaudiologoRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return hasattr(self.request.user, 'fonoaudiologo')


class PacienteRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return hasattr(self.request.user, 'paciente_perfil')


def url_agenda(data=None):
    """URL do painel já aberto na aba 'Minha Agenda' (e, opcionalmente, num dia da Agenda do Dia)."""
    url = reverse('dashboard_fono') + '?tab=agenda'
    if data:
        url += f'&data={data}'
    return url


def destino_seguro(request, padrao):
    """Usa o parâmetro `next` se ele apontar para este próprio site; senão, o destino padrão."""
    destino = request.POST.get('next') or request.GET.get('next')
    if destino and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()},
                                                   require_https=request.is_secure()):
        return destino
    return padrao


class RetornoAgendaMixin:
    """Após editar/excluir/confirmar um agendamento, volta para a mesma tela da agenda."""

    def get_success_url(self):
        return destino_seguro(self.request, url_agenda())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['voltar_url'] = destino_seguro(self.request, url_agenda())
        return context


def nome_profissional(fono):
    return fono.user.get_full_name() or fono.user.username


def calcular_idade(nascimento, referencia=None):
    if not nascimento:
        return None
    referencia = referencia or timezone.localdate()
    return referencia.year - nascimento.year - ((referencia.month, referencia.day) < (nascimento.month, nascimento.day))


def contexto_atividade(material=None, paciente=None, fono=None, titulo='', conteudo='', data_atividade=None, numero=''):
    paciente = paciente or material.paciente
    fono = fono or paciente.fonoaudiologo
    return {
        'paciente': paciente,
        'fono': fono,
        'fono_nome': nome_profissional(fono),
        'clinica': paciente.clinica,
        'titulo': titulo or (material.titulo if material else 'Atividade para Casa'),
        'conteudo': conteudo or (material.conteudo_atividade if material else ''),
        'data_atividade': data_atividade or (timezone.localtime(material.data_upload) if material else timezone.localtime()),
        'primeiro_nome': (paciente.nome.split() or [paciente.nome])[0],
        'tipo_documento': 'ATIVIDADE PARA CASA',
        'numero_documento': numero or (f'ATV-{material.pk:05d}' if material and material.pk else 'ATV-NOVA'),
    }


class HomeView(TemplateView):
    template_name = 'clinica/home.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if hasattr(request.user, 'fonoaudiologo'):
                return redirect('dashboard_fono')
            elif hasattr(request.user, 'paciente_perfil'):
                return redirect('area_paciente')
            elif request.user.is_superuser:
                return redirect('/admin/')
        return super().get(request, *args, **kwargs)


class DashboardFonoView(LoginRequiredMixin, FonoaudiologoRequiredMixin, ListView):
    model = Paciente
    template_name = 'clinica/dashboard_fono.html'
    context_object_name = 'pacientes'

    def get_queryset(self):
        return Paciente.objects.filter(fonoaudiologo=self.request.user.fonoaudiologo).select_related('clinica')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fono = self.request.user.fonoaudiologo
        agendamentos = Agendamento.objects.filter(fonoaudiologo=fono).select_related('paciente', 'clinica').order_by('data_hora')
        context['agendamentos'] = agendamentos

        # Agendamentos pendentes de confirmação (status='P')
        agendamentos_pendentes_list = agendamentos.filter(status='P').order_by('data_hora')
        context['agendamentos_pendentes_list'] = agendamentos_pendentes_list

        # Aba "Minha Agenda": todos os agendamentos ativos (pendentes, confirmados e realizados)
        agendamentos_confirmados = agendamentos.filter(status__in=['P', 'A', 'R']).order_by('data_hora')
        context['agendamentos_confirmados'] = agendamentos_confirmados

        if 'agendamento_form' not in context:
            context['agendamento_form'] = AgendamentoForm(fonoaudiologo=fono)
        # Dados para o assistente no dashboard
        hoje = timezone.localdate()
        context['agendamentos_hoje'] = agendamentos.filter(
            data_hora__date=hoje, status__in=['A', 'P']
        ).count()
        context['proximo_agendamento'] = agendamentos.filter(
            data_hora__gte=timezone.now(), status__in=['A', 'P']
        ).first()
        context['agendamentos_pendentes'] = agendamentos_pendentes_list.count()

        # Filtragem da Agenda do Dia
        date_str = self.request.GET.get('data')
        selected_date = hoje
        if date_str:
            try:
                selected_date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                selected_date = hoje

        context['selected_date'] = selected_date
        context['agendamentos_dia'] = itens_agenda(fono, selected_date, selected_date)
        context['prev_date'] = (selected_date - timedelta(days=1)).strftime('%Y-%m-%d')
        context['next_date'] = (selected_date + timedelta(days=1)).strftime('%Y-%m-%d')
        context['hoje_date'] = hoje.strftime('%Y-%m-%d')

        tab = self.request.GET.get('tab')
        context['active_tab'] = tab if tab in ('pacientes', 'agenda') else 'pacientes'
        data_param = None if selected_date == hoje else selected_date.strftime('%Y-%m-%d')
        context['agenda_retorno'] = url_agenda(data_param)

        # Rótulo dinâmico da data para a Agenda do Dia
        diff_days = (selected_date - hoje).days
        is_hoje = (diff_days == 0)
        dias_semana = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
        dias_semana_abrev = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
        dia_nome = dias_semana[selected_date.weekday()]
        dia_abrev = dias_semana_abrev[selected_date.weekday()]

        if is_hoje:
            data_rotulo = f"Hoje ({selected_date.strftime('%d/%m')})"
            data_rotulo_curto = "Hoje"
            titulo_consultas = f"Consultas de Hoje ({selected_date.strftime('%d/%m/%Y')})"
        elif diff_days == 1:
            data_rotulo = f"Amanhã ({selected_date.strftime('%d/%m')})"
            data_rotulo_curto = "Amanhã"
            titulo_consultas = f"Consultas de Amanhã ({selected_date.strftime('%d/%m/%Y')})"
        elif diff_days == -1:
            data_rotulo = f"Ontem ({selected_date.strftime('%d/%m')})"
            data_rotulo_curto = "Ontem"
            titulo_consultas = f"Consultas de Ontem ({selected_date.strftime('%d/%m/%Y')})"
        else:
            data_rotulo = f"{dia_abrev}, {selected_date.strftime('%d/%m')}"
            data_rotulo_curto = selected_date.strftime('%d/%m/%Y')
            titulo_consultas = f"Consultas de {dia_nome} ({selected_date.strftime('%d/%m/%Y')})"

        context['is_hoje'] = is_hoje
        context['data_rotulo'] = data_rotulo
        context['data_rotulo_curto'] = data_rotulo_curto
        context['titulo_consultas'] = titulo_consultas

        return context

    def post(self, request, *args, **kwargs):
        fono = request.user.fonoaudiologo
        form = AgendamentoForm(request.POST, fonoaudiologo=fono)
        if form.is_valid():
            agendamento = form.save(commit=False)
            agendamento.fonoaudiologo = fono
            # Agendado pelo próprio profissional: já entra confirmado na agenda.
            agendamento.status = 'A'
            agendamento.confirmado_em = timezone.now()
            agendamento.save()
            messages.success(request, 'Agendamento criado com sucesso.')
            data = timezone.localtime(agendamento.data_hora).strftime('%Y-%m-%d')
            return redirect(url_agenda(data))
        self.object_list = self.get_queryset()
        context = self.get_context_data(agendamento_form=form)
        context['active_tab'] = 'agenda'
        context['abrir_modal_agendamento'] = True
        return self.render_to_response(context)


class AgendaMensalView(LoginRequiredMixin, FonoaudiologoRequiredMixin, View):
    """Dados (JSON) da agenda personalizada do mês, usada no calendário do painel."""

    def get(self, request):
        hoje = timezone.localdate()
        try:
            ano = int(request.GET.get('ano', hoje.year))
            mes = int(request.GET.get('mes', hoje.month))
        except (TypeError, ValueError):
            return JsonResponse({'erro': 'Parâmetros de data inválidos.'}, status=400)
        if not (1 <= mes <= 12 and 1900 <= ano <= 2200):
            return JsonResponse({'erro': 'Mês ou ano fora do intervalo permitido.'}, status=400)

        inicio = date(ano, mes, 1)
        fim = date(ano, mes, calendar.monthrange(ano, mes)[1])
        itens = itens_agenda(request.user.fonoaudiologo, inicio, fim)

        resumo = {'total': 0, 'P': 0, 'A': 0, 'R': 0, 'C': 0, 'S': 0}
        for item in itens:
            resumo[item['status']] = resumo.get(item['status'], 0) + 1
            if item['status'] != 'C':
                resumo['total'] += 1

        anterior = inicio - timedelta(days=1)
        proximo = fim + timedelta(days=1)
        return JsonResponse({
            'ano': ano,
            'mes': mes,
            'titulo': f'{MESES[mes - 1]} de {ano}',
            'hoje': hoje.strftime('%Y-%m-%d'),
            'anterior': {'ano': anterior.year, 'mes': anterior.month},
            'proximo': {'ano': proximo.year, 'mes': proximo.month},
            'resumo': resumo,
            'eventos': [item_para_json(i) for i in itens],
        })


class PacienteDetailView(LoginRequiredMixin, FonoaudiologoRequiredMixin, DetailView):
    model = Paciente
    template_name = 'clinica/paciente_detail.html'
    context_object_name = 'paciente'

    def get_queryset(self):
        return Paciente.objects.filter(fonoaudiologo=self.request.user.fonoaudiologo)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['materiais'] = self.object.materiais.all().order_by('-data_upload')
        context['consultas'] = self.object.consultas.all().order_by('-data_hora')
        datas = [c.data_hora.strftime("%d/%m") for c in reversed(list(context['consultas']))]
        notas = [c.desempenho_nota for c in reversed(list(context['consultas']))]
        context['chart_labels'] = datas
        context['chart_data'] = notas
        context.setdefault('consulta_form', ConsultaForm())
        context.setdefault('material_form', MaterialUploadForm())
        tab = self.request.GET.get('tab')
        context['active_tab'] = tab if tab in ('evolucao', 'consultas', 'materiais') else 'evolucao'
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if 'material_upload' in request.POST:
            material_form = MaterialUploadForm(request.POST, request.FILES)
            if material_form.is_valid():
                material = material_form.save(commit=False)
                material.paciente = self.object
                material.save()
                messages.success(request, 'Material enviado com sucesso.')
                return redirect(reverse('paciente_detail', args=[self.object.id]) + '?tab=materiais')
            context = self.get_context_data(object=self.object, material_form=material_form)
            context['active_tab'] = 'materiais'
            context['abrir_modal'] = 'uploadMaterialModal'
            return self.render_to_response(context)

        form = ConsultaForm(request.POST)
        if form.is_valid():
            consulta = form.save(commit=False)
            consulta.paciente = self.object
            consulta.save()
            messages.success(request, 'Consulta registrada com sucesso.')
            return redirect(reverse('paciente_detail', args=[self.object.id]) + '?tab=consultas')
        context = self.get_context_data(object=self.object, consulta_form=form)
        context['active_tab'] = 'consultas'
        context['abrir_modal'] = 'novaConsultaModal'
        return self.render_to_response(context)


class AreaPacienteView(LoginRequiredMixin, PacienteRequiredMixin, ListView):
    model = MaterialDidatico
    template_name = 'clinica/area_paciente.html'
    context_object_name = 'materiais'

    def get_queryset(self):
        return MaterialDidatico.objects.filter(paciente=self.request.user.paciente_perfil).order_by('-data_upload')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        consultas = self.request.user.paciente_perfil.consultas.all().order_by('-data_hora')
        context['consultas'] = consultas
        context['agendamentos'] = Agendamento.objects.filter(
            paciente=self.request.user.paciente_perfil,
            fonoaudiologo=self.request.user.paciente_perfil.fonoaudiologo,
            status__in=['A', 'P']
        ).select_related('fonoaudiologo__user', 'clinica').order_by('data_hora')
        datas = [c.data_hora.strftime("%d/%m") for c in reversed(list(consultas))]
        notas = [c.desempenho_nota for c in reversed(list(consultas))]
        context['chart_labels'] = datas
        context['chart_data'] = notas
        return context


class PacienteAgendamentoCreateView(LoginRequiredMixin, PacienteRequiredMixin, CreateView):
    model = Agendamento
    form_class = PacienteAgendamentoForm
    template_name = 'clinica/paciente_agendamento_form.html'
    success_url = reverse_lazy('area_paciente')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['fonoaudiologo'] = self.request.user.paciente_perfil.fonoaudiologo
        return kwargs

    def form_valid(self, form):
        paciente = self.request.user.paciente_perfil
        agendamento = form.save(commit=False)
        agendamento.paciente = paciente
        agendamento.fonoaudiologo = paciente.fonoaudiologo
        agendamento.status = 'P'  # Pendente de confirmação
        agendamento.save()
        messages.success(self.request, 'Consulta agendada com sucesso! Seu fonoaudiólogo receberá a solicitação e confirmará em breve.')
        return super().form_valid(form)


class ExportarProntuarioPDFView(LoginRequiredMixin, FonoaudiologoRequiredMixin, View):
    def get(self, request, pk, *args, **kwargs):
        paciente = get_object_or_404(
            Paciente.objects.select_related('clinica', 'fonoaudiologo__user'),
            pk=pk, fonoaudiologo=request.user.fonoaudiologo,
        )
        consultas = list(paciente.consultas.all().order_by('data_hora'))
        notas = [c.desempenho_nota for c in consultas]

        tendencia = '—'
        if len(notas) >= 2:
            janela = max(1, min(3, len(notas) // 2))
            inicio = sum(notas[:janela]) / janela
            fim = sum(notas[-janela:]) / janela
            if fim - inicio >= 0.5:
                tendencia = 'Melhora'
            elif inicio - fim >= 0.5:
                tendencia = 'Queda'
            else:
                tendencia = 'Estável'

        emitido = timezone.localtime()
        fono = paciente.fonoaudiologo
        context = {
            'paciente': paciente,
            'consultas': consultas,
            'fono': fono,
            'fono_nome': nome_profissional(fono),
            'clinica': paciente.clinica,
            'idade': calcular_idade(paciente.data_nascimento),
            'resumo': {
                'total': len(consultas),
                'primeira': consultas[0].data_hora if consultas else None,
                'ultima': consultas[-1].data_hora if consultas else None,
                'media': (sum(notas) / len(notas)) if notas else None,
                'tendencia': tendencia,
            },
            'tipo_documento': 'PRONTUÁRIO FONOAUDIOLÓGICO',
            'numero_documento': f'PRT-{paciente.pk:05d}-{emitido:%Y%m%d}',
        }
        pdf = gerar_pdf_bytes('clinica/pdfs/relatorio_evolucao.html', context)
        if pdf is None:
            messages.error(request, 'Não foi possível gerar o PDF do prontuário. Tente novamente.')
            return redirect('paciente_detail', pk=paciente.pk)
        return resposta_pdf(pdf, nome_arquivo_seguro('prontuario', paciente.nome, emitido.strftime('%Y-%m-%d')))


class GerarAtividadePDFView(LoginRequiredMixin, FonoaudiologoRequiredMixin, View):
    def get(self, request, pk, *args, **kwargs):
        paciente = get_object_or_404(Paciente, pk=pk, fonoaudiologo=request.user.fonoaudiologo)
        form = GerarAtividadeForm()
        return render(request, 'clinica/gerar_atividade.html', {'form': form, 'paciente': paciente})

    def post(self, request, pk, *args, **kwargs):
        paciente = get_object_or_404(Paciente.objects.select_related('clinica'), pk=pk, fonoaudiologo=request.user.fonoaudiologo)
        form = GerarAtividadeForm(request.POST)
        if form.is_valid():
            titulo = form.cleaned_data['titulo']
            conteudo = form.cleaned_data['conteudo_atividade']
            material = MaterialDidatico.objects.create(
                paciente=paciente,
                titulo=titulo,
                descricao="Gerado automaticamente via sistema.",
                conteudo_atividade=conteudo,
            )
            pdf = gerar_pdf_bytes('clinica/pdfs/atividade_personalizada.html', contexto_atividade(material))
            if pdf is None:
                material.delete()
                messages.error(request, 'Não foi possível gerar o PDF da atividade. Tente novamente.')
            else:
                material.arquivo.save(nome_arquivo_seguro('atividade', titulo, paciente.nome), ContentFile(pdf))
                messages.success(request, 'Atividade gerada e enviada para a área do paciente.')
                return redirect(reverse('paciente_detail', args=[paciente.id]) + '?tab=materiais')
        return render(request, 'clinica/gerar_atividade.html', {'form': form, 'paciente': paciente})


class MaterialDownloadView(LoginRequiredMixin, View):
    """
    Entrega um material didático apenas para o paciente dono dele ou para o
    fonoaudiólogo responsável. Atividades geradas pelo sistema são sempre
    renderizadas com o modelo institucional atual.
    """

    def get(self, request, pk):
        material = get_object_or_404(
            MaterialDidatico.objects.select_related('paciente__fonoaudiologo__user', 'paciente__clinica'), pk=pk
        )
        user = request.user
        eh_fono = hasattr(user, 'fonoaudiologo') and material.paciente.fonoaudiologo_id == user.fonoaudiologo.id
        eh_paciente = hasattr(user, 'paciente_perfil') and material.paciente_id == user.paciente_perfil.id
        if not (eh_fono or eh_paciente):
            raise Http404('Material não encontrado.')

        inline = request.GET.get('inline') == '1'
        if material.gerado_pelo_sistema:
            pdf = gerar_pdf_bytes('clinica/pdfs/atividade_personalizada.html', contexto_atividade(material))
            if pdf is not None:
                return resposta_pdf(pdf, nome_arquivo_seguro('atividade', material.titulo, material.paciente.nome), inline=inline)
        if material.arquivo:
            try:
                arquivo = material.arquivo.open('rb')
            except (FileNotFoundError, OSError):
                raise Http404('Arquivo não encontrado.')
            return FileResponse(arquivo, as_attachment=not inline, filename=os.path.basename(material.arquivo.name))
        if material.link_externo:
            return redirect(material.link_externo)
        raise Http404('Material sem arquivo.')


class CadastroFonoView(View):
    def get(self, request):
        form = FonoaudiologoCadastroForm()
        return render(request, 'clinica/cadastro_fono.html', {'form': form})

    def post(self, request):
        form = FonoaudiologoCadastroForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                email=form.cleaned_data['email']
            )
            fono = form.save(commit=False)
            fono.user = user
            fono.save()
            messages.success(request, 'Cadastro realizado com sucesso. Faça login para continuar.')
            return redirect('login')
        return render(request, 'clinica/cadastro_fono.html', {'form': form})


class CadastroPacienteView(View):
    def get(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'fonoaudiologo'):
            form = FonoCadastraPacienteForm(fonoaudiologo=request.user.fonoaudiologo)
            return render(request, 'clinica/cadastro_paciente.html', {'form': form, 'is_fono': True})
        form = PacienteCadastroForm()
        return render(request, 'clinica/cadastro_paciente.html', {'form': form, 'is_fono': False})

    def post(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'fonoaudiologo'):
            fono = request.user.fonoaudiologo
            form = FonoCadastraPacienteForm(request.POST, fonoaudiologo=fono)
            if form.is_valid():
                paciente = form.save(commit=False)
                paciente.fonoaudiologo = fono

                criar_acesso = form.cleaned_data.get('criar_acesso')
                if criar_acesso:
                    user = User.objects.create_user(
                        username=form.cleaned_data['username'],
                        password=form.cleaned_data['password'],
                        first_name=form.cleaned_data['nome']
                    )
                    paciente.user = user

                paciente.save()
                messages.success(request, f'Paciente {paciente.nome} cadastrado com sucesso!')
                return redirect('paciente_detail', pk=paciente.pk)

            return render(request, 'clinica/cadastro_paciente.html', {'form': form, 'is_fono': True})

        form = PacienteCadastroForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['nome']
            )
            paciente = form.save(commit=False)
            paciente.user = user
            paciente.save()
            messages.success(request, 'Conta criada com sucesso! Faça login para continuar.')
            return redirect('login')
        return render(request, 'clinica/cadastro_paciente.html', {'form': form, 'is_fono': False})


class PacienteUpdateView(LoginRequiredMixin, FonoaudiologoRequiredMixin, UpdateView):
    model = Paciente
    form_class = PacienteUpdateForm
    template_name = 'clinica/paciente_form.html'

    def get_queryset(self):
        return Paciente.objects.filter(fonoaudiologo=self.request.user.fonoaudiologo)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['fonoaudiologo'] = self.request.user.fonoaudiologo
        return kwargs

    def get_success_url(self):
        return reverse('paciente_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Dados do paciente atualizados com sucesso.')
        return super().form_valid(form)


class AgendamentoUpdateView(LoginRequiredMixin, FonoaudiologoRequiredMixin, RetornoAgendaMixin, UpdateView):
    model = Agendamento
    form_class = AgendamentoForm
    template_name = 'clinica/agendamento_form.html'

    def get_queryset(self):
        return Agendamento.objects.filter(fonoaudiologo=self.request.user.fonoaudiologo)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['fonoaudiologo'] = self.request.user.fonoaudiologo
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Agendamento atualizado com sucesso.')
        return super().form_valid(form)


class AgendamentoDeleteView(LoginRequiredMixin, FonoaudiologoRequiredMixin, RetornoAgendaMixin, DeleteView):
    model = Agendamento
    template_name = 'clinica/agendamento_confirm_delete.html'

    def get_queryset(self):
        return Agendamento.objects.filter(fonoaudiologo=self.request.user.fonoaudiologo)

    def form_valid(self, form):
        messages.success(self.request, 'Agendamento excluído com sucesso.')
        return super().form_valid(form)


# ─────────────────────────────────────────────────────────────────────────────────
# Módulo de Clínicas
# ─────────────────────────────────────────────────────────────────────────────────

class ClinicaListView(LoginRequiredMixin, FonoaudiologoRequiredMixin, ListView):
    model = Clinica
    template_name = 'clinica/clinica_list.html'
    context_object_name = 'clinicas'
    paginate_by = 10

    def get_queryset(self):
        fono = self.request.user.fonoaudiologo
        qs = fono.clinicas.all()
        q = self.request.GET.get('q', '')
        status = self.request.GET.get('status', '')
        if q:
            qs = qs.filter(Q(nome__icontains=q) | Q(cidade__icontains=q) | Q(cnpj__icontains=q))
        if status == 'ativa':
            qs = qs.filter(ativo=True)
        elif status == 'inativa':
            qs = qs.filter(ativo=False)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context['status_filter'] = self.request.GET.get('status', '')
        return context


class ClinicaCreateView(LoginRequiredMixin, FonoaudiologoRequiredMixin, CreateView):
    model = Clinica
    form_class = ClinicaForm
    template_name = 'clinica/clinica_form.html'
    success_url = reverse_lazy('clinica_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.fonoaudiologos.add(self.request.user.fonoaudiologo)
        messages.success(self.request, 'Clínica cadastrada e vinculada com sucesso.')
        return response


class ClinicaDetailView(LoginRequiredMixin, FonoaudiologoRequiredMixin, DetailView):
    model = Clinica
    template_name = 'clinica/clinica_detail.html'
    context_object_name = 'clinica'

    def get_queryset(self):
        return self.request.user.fonoaudiologo.clinicas.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['fonoaudiologos_vinculados'] = self.object.fonoaudiologos.select_related('user').all()
        context['todos_fonos'] = Fonoaudiologo.objects.select_related('user').exclude(
            pk__in=self.object.fonoaudiologos.values_list('pk', flat=True)
        )
        context['pacientes_vinculados'] = self.object.pacientes.select_related('fonoaudiologo__user').all()
        return context


class ClinicaUpdateView(LoginRequiredMixin, FonoaudiologoRequiredMixin, UpdateView):
    model = Clinica
    form_class = ClinicaForm
    template_name = 'clinica/clinica_form.html'
    success_url = reverse_lazy('clinica_list')

    def get_queryset(self):
        return self.request.user.fonoaudiologo.clinicas.all()

    def form_valid(self, form):
        messages.success(self.request, 'Clínica atualizada com sucesso.')
        return super().form_valid(form)


class ClinicaDeleteView(LoginRequiredMixin, FonoaudiologoRequiredMixin, DeleteView):
    model = Clinica
    template_name = 'clinica/clinica_confirm_delete.html'
    success_url = reverse_lazy('clinica_list')

    def get_queryset(self):
        return self.request.user.fonoaudiologo.clinicas.all()

    def form_valid(self, form):
        messages.success(self.request, 'Clínica excluída com sucesso.')
        return super().form_valid(form)


# ─────────────────────────────────────────────────────────────────────────────────
# Vínculo Médico ↔ Clínica
# ─────────────────────────────────────────────────────────────────────────────────

class VincularFonoClinicaView(LoginRequiredMixin, FonoaudiologoRequiredMixin, View):
    def post(self, request, clinica_pk, fono_pk):
        clinica = get_object_or_404(request.user.fonoaudiologo.clinicas.all(), pk=clinica_pk)
        fono = get_object_or_404(Fonoaudiologo, pk=fono_pk)
        clinica.fonoaudiologos.add(fono)
        messages.success(request, f'{fono} vinculado à clínica {clinica} com sucesso.')
        return redirect('clinica_detail', pk=clinica_pk)


class DesvincularFonoClinicaView(LoginRequiredMixin, FonoaudiologoRequiredMixin, View):
    def post(self, request, clinica_pk, fono_pk):
        clinica = get_object_or_404(request.user.fonoaudiologo.clinicas.all(), pk=clinica_pk)
        fono = get_object_or_404(Fonoaudiologo, pk=fono_pk)
        clinica.fonoaudiologos.remove(fono)
        messages.success(request, 'Vínculo removido com sucesso.')
        if fono == request.user.fonoaudiologo:
            return redirect('clinica_list')
        return redirect('clinica_detail', pk=clinica_pk)


class MaterialDeleteView(LoginRequiredMixin, FonoaudiologoRequiredMixin, DeleteView):
    model = MaterialDidatico
    template_name = 'clinica/material_confirm_delete.html'

    def get_queryset(self):
        fono = self.request.user.fonoaudiologo
        return MaterialDidatico.objects.filter(paciente__fonoaudiologo=fono)

    def get_success_url(self):
        return reverse('paciente_detail', kwargs={'pk': self.object.paciente.id}) + '?tab=materiais'

    def form_valid(self, form):
        messages.success(self.request, 'Material didático excluído com sucesso.')
        return super().form_valid(form)


# ─────────────────────────────────────────────────────────────────────────────────
# Gerenciamento de Disponibilidades e Agendamentos
# ─────────────────────────────────────────────────────────────────────────────────

class DisponibilidadeHorariaListView(LoginRequiredMixin, FonoaudiologoRequiredMixin, ListView):
    model = DisponibilidadeHoraria
    template_name = 'clinica/disponibilidade_list.html'
    context_object_name = 'disponibilidades'
    paginate_by = 10

    def get_queryset(self):
        fono = self.request.user.fonoaudiologo
        return DisponibilidadeHoraria.objects.filter(fonoaudiologo=fono).select_related('clinica').order_by('dia_semana', 'hora_inicio')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clinicas'] = self.request.user.fonoaudiologo.clinicas.filter(ativo=True)
        return context


class DisponibilidadeHorariaCreateView(LoginRequiredMixin, FonoaudiologoRequiredMixin, CreateView):
    model = DisponibilidadeHoraria
    form_class = DisponibilidadeHorariaForm
    template_name = 'clinica/disponibilidade_form.html'
    success_url = reverse_lazy('disponibilidade_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['fonoaudiologo'] = self.request.user.fonoaudiologo
        return kwargs

    def form_valid(self, form):
        form.instance.fonoaudiologo = self.request.user.fonoaudiologo
        messages.success(self.request, 'Horário de disponibilidade registrado com sucesso.')
        return super().form_valid(form)


class DisponibilidadeHorariaUpdateView(LoginRequiredMixin, FonoaudiologoRequiredMixin, UpdateView):
    model = DisponibilidadeHoraria
    form_class = DisponibilidadeHorariaForm
    template_name = 'clinica/disponibilidade_form.html'
    success_url = reverse_lazy('disponibilidade_list')

    def get_queryset(self):
        fono = self.request.user.fonoaudiologo
        return DisponibilidadeHoraria.objects.filter(fonoaudiologo=fono)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['fonoaudiologo'] = self.request.user.fonoaudiologo
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Horário de disponibilidade atualizado com sucesso.')
        return super().form_valid(form)


class DisponibilidadeHorariaDeleteView(LoginRequiredMixin, FonoaudiologoRequiredMixin, DeleteView):
    model = DisponibilidadeHoraria
    template_name = 'clinica/disponibilidade_confirm_delete.html'
    success_url = reverse_lazy('disponibilidade_list')

    def get_queryset(self):
        fono = self.request.user.fonoaudiologo
        return DisponibilidadeHoraria.objects.filter(fonoaudiologo=fono)

    def form_valid(self, form):
        messages.success(self.request, 'Horário de disponibilidade removido com sucesso.')
        return super().form_valid(form)


class AgendamentosPendentesView(LoginRequiredMixin, FonoaudiologoRequiredMixin, ListView):
    model = Agendamento
    template_name = 'clinica/agendamentos_pendentes.html'
    context_object_name = 'agendamentos'
    paginate_by = 10

    def get_queryset(self):
        fono = self.request.user.fonoaudiologo
        return Agendamento.objects.filter(fonoaudiologo=fono, status='P').select_related('paciente', 'clinica').order_by('data_hora')


class ConfirmarAgendamentoView(LoginRequiredMixin, FonoaudiologoRequiredMixin, UpdateView):
    model = Agendamento
    form_class = ConfirmarAgendamentoForm
    template_name = 'clinica/confirmar_agendamento.html'
    success_url = reverse_lazy('dashboard_fono')

    def get_queryset(self):
        fono = self.request.user.fonoaudiologo
        return Agendamento.objects.filter(fonoaudiologo=fono, status='P')

    def get_success_url(self):
        return destino_seguro(self.request, str(self.success_url))

    def form_valid(self, form):
        agendamento = form.save(commit=False)
        agendamento.status = 'A'
        agendamento.confirmado_em = timezone.now()
        agendamento.save()
        messages.success(self.request, '✓ Agendamento confirmado com sucesso!')
        return super().form_valid(form)


class RejeitarAgendamentoView(LoginRequiredMixin, FonoaudiologoRequiredMixin, UpdateView):
    model = Agendamento
    form_class = RejeitarAgendamentoForm
    template_name = 'clinica/rejeitar_agendamento.html'
    success_url = reverse_lazy('dashboard_fono')

    def get_queryset(self):
        fono = self.request.user.fonoaudiologo
        return Agendamento.objects.filter(fonoaudiologo=fono, status='P')

    def get_success_url(self):
        return destino_seguro(self.request, str(self.success_url))

    def form_valid(self, form):
        agendamento = form.save(commit=False)
        agendamento.status = 'C'
        agendamento.save()
        messages.success(self.request, '✗ Agendamento rejeitado com sucesso.')
        return super().form_valid(form)


class AssistenteView(LoginRequiredMixin, FonoaudiologoRequiredMixin, View):
    template_name = 'clinica/assistente.html'

    def get(self, request):
        fono = request.user.fonoaudiologo
        agora = timezone.now()
        hoje = timezone.localdate()

        # Agendamentos de hoje
        agendamentos_hoje = Agendamento.objects.filter(
            fonoaudiologo=fono,
            data_hora__date=hoje,
            status__in=['A', 'P']
        ).select_related('paciente', 'clinica').order_by('data_hora')

        # Próximo agendamento confirmado
        proximo = agendamentos_hoje.filter(data_hora__gte=agora, status='A').first()

        # Agendamentos pendentes (todos os status que precisam de confirmação)
        agendamentos_pendentes = Agendamento.objects.filter(
            fonoaudiologo=fono,
            status='P'
        ).select_related('paciente', 'clinica').order_by('data_hora')

        # Detectar conflitos (2 agendamentos com menos de 30min de diferença)
        conflitos = []
        lista = list(agendamentos_hoje)
        for i in range(len(lista) - 1):
            diff = (lista[i+1].data_hora - lista[i].data_hora).total_seconds() / 60
            if diff < 30:
                conflitos.append((lista[i], lista[i+1]))

        # Próximos 7 dias
        proximos_7_dias = Agendamento.objects.filter(
            fonoaudiologo=fono,
            data_hora__gte=agora,
            data_hora__lte=agora + timedelta(days=7),
            status__in=['A', 'P']
        ).select_related('paciente', 'clinica').order_by('data_hora')

        # Clínicas do fonoaudiólogo
        clinicas = fono.clinicas.filter(ativo=True)

        # Disponibilidades ativas
        disponibilidades_ativas = DisponibilidadeHoraria.objects.filter(
            fonoaudiologo=fono,
            ativo=True
        ).count()

        # Pacientes do fonoaudiólogo
        total_pacientes = Paciente.objects.filter(fonoaudiologo=fono).count()

        context = {
            'agendamentos_hoje': agendamentos_hoje,
            'total_hoje': agendamentos_hoje.count(),
            'proximo': proximo,
            'conflitos': conflitos,
            'proximos_7_dias': proximos_7_dias,
            'agendamentos_pendentes': agendamentos_pendentes,
            'total_pendentes': agendamentos_pendentes.count(),
            'total_pacientes': total_pacientes,
            'clinicas': clinicas,
            'total_clinicas': clinicas.count(),
            'disponibilidades_ativas': disponibilidades_ativas,
        }
        return render(request, self.template_name, context)


# ─────────────────────────────────────────────────────────────────────────────────
# Perfil e preferências do usuário
# ─────────────────────────────────────────────────────────────────────────────────

class PerfilView(LoginRequiredMixin, View):
    template_name = 'clinica/perfil.html'

    def _forms(self, request, data=None, files=None):
        user = request.user
        perfil = PerfilUsuario.para(user)
        forms = {
            'dados_form': UsuarioDadosForm(data, instance=user, prefix='dados'),
            'preferencias_form': PerfilPreferenciasForm(data, files, instance=perfil, prefix='pref'),
        }
        if hasattr(user, 'fonoaudiologo'):
            forms['extra_form'] = FonoaudiologoPerfilForm(data, instance=user.fonoaudiologo, prefix='extra')
        elif hasattr(user, 'paciente_perfil'):
            forms['extra_form'] = PacientePerfilForm(data, instance=user.paciente_perfil, prefix='extra')
        return perfil, forms

    def _render(self, request, perfil, forms):
        context = {'perfil': perfil, **forms}
        return render(request, self.template_name, context)

    def get(self, request):
        perfil, forms = self._forms(request)
        return self._render(request, perfil, forms)

    def post(self, request):
        perfil, forms = self._forms(request, request.POST, request.FILES)
        if all(f.is_valid() for f in forms.values()):
            for f in forms.values():
                f.save()
            messages.success(request, 'Perfil atualizado com sucesso.')
            return redirect('perfil')
        messages.error(request, 'Revise os campos destacados.')
        return self._render(request, perfil, forms)


class AlterarSenhaView(auth_views.PasswordChangeView):
    template_name = 'clinica/alterar_senha.html'
    success_url = reverse_lazy('perfil')

    def form_valid(self, form):
        messages.success(self.request, 'Senha alterada com sucesso.')
        return super().form_valid(form)


# ─────────────────────────────────────────────────────────────────────────────────
# Termos, Privacidade e LGPD
# ─────────────────────────────────────────────────────────────────────────────────

class TermosUsoView(TemplateView):
    template_name = 'clinica/termos.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['termo'] = TermoVersao.objects.filter(tipo='uso', ativo=True).first()
        return context


class PoliticaPrivacidadeView(TemplateView):
    template_name = 'clinica/politica_privacidade.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['termo'] = TermoVersao.objects.filter(tipo='privacidade', ativo=True).first()
        return context


class AceitarTermosView(LoginRequiredMixin, View):
    template_name = 'clinica/aceitar_termos.html'

    def _get_termos_pendentes(self, user):
        aceitos_ids = TermoAceite.objects.filter(user=user).values_list('termo_id', flat=True)
        return TermoVersao.objects.filter(ativo=True).exclude(pk__in=aceitos_ids)

    def get(self, request):
        termos_pendentes = self._get_termos_pendentes(request.user)
        if not termos_pendentes.exists():
            return redirect('home')
        return render(request, self.template_name, {'termos_pendentes': termos_pendentes})

    def post(self, request):
        termos_pendentes = self._get_termos_pendentes(request.user)
        ip = request.META.get('REMOTE_ADDR')
        for termo in termos_pendentes:
            TermoAceite.objects.get_or_create(user=request.user, termo=termo, defaults={'ip': ip})
        messages.success(request, 'Termos aceitos com sucesso. Bem-vindo ao FonoGestão!')
        return redirect('home')
