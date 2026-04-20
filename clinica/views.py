from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse, reverse_lazy
from django.http import HttpResponse
from django.core.files.base import ContentFile
from django.contrib.auth.models import User
from django.views.generic.edit import UpdateView, DeleteView
from .models import Paciente, MaterialDidatico, Fonoaudiologo, Consulta, Agendamento
from .forms import ConsultaForm, AgendamentoForm, GerarAtividadeForm, FonoaudiologoCadastroForm, PacienteCadastroForm, MaterialUploadForm
from .utils import render_to_pdf

class FonoaudiologoRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return hasattr(self.request.user, 'fonoaudiologo')

class PacienteRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return hasattr(self.request.user, 'paciente_perfil')

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
        return Paciente.objects.filter(fonoaudiologo=self.request.user.fonoaudiologo)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Passar formulário de agendamento e lista de agendamentos futuros
        context['agendamentos'] = Agendamento.objects.filter(
            fonoaudiologo=self.request.user.fonoaudiologo
        ).order_by('data_hora')
        
        if 'agendamento_form' not in context:
            form = AgendamentoForm()
            form.fields['paciente'].queryset = self.get_queryset()
            context['agendamento_form'] = form
        return context

    def post(self, request, *args, **kwargs):
        form = AgendamentoForm(request.POST)
        if form.is_valid():
            agendamento = form.save(commit=False)
            agendamento.fonoaudiologo = request.user.fonoaudiologo
            agendamento.save()
            return redirect('dashboard_fono')
        
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        context['agendamento_form'] = form
        return self.render_to_response(context)


class PacienteDetailView(LoginRequiredMixin, FonoaudiologoRequiredMixin, DetailView):
    model = Paciente
    template_name = 'clinica/paciente_detail.html'
    context_object_name = 'paciente'

    def get_queryset(self):
        # Garante que o fonoaudiólogo só acesse seus próprios pacientes
        return Paciente.objects.filter(fonoaudiologo=self.request.user.fonoaudiologo)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['materiais'] = self.object.materiais.all().order_by('-data_upload')
        context['consultas'] = self.object.consultas.all().order_by('-data_hora')
        
        # Para o gráfico (Chart.js)
        # Precisamos passar os rótulos (datas) e os dados (notas)
        datas = [c.data_hora.strftime("%d/%m") for c in reversed(context['consultas'])]
        notas = [c.desempenho_nota for c in reversed(context['consultas'])]
        context['chart_labels'] = datas
        context['chart_data'] = notas
        # Formulários
        context['consulta_form'] = ConsultaForm()
        context['material_form'] = MaterialUploadForm()
        
        return context
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        if 'material_upload' in request.POST:
            material_form = MaterialUploadForm(request.POST, request.FILES)
            if material_form.is_valid():
                material = material_form.save(commit=False)
                material.paciente = self.object
                material.save()
                return redirect('paciente_detail', pk=self.object.id)
        else:
            form = ConsultaForm(request.POST)
            if form.is_valid():
                consulta = form.save(commit=False)
                consulta.paciente = self.object
                consulta.save()
                return redirect('paciente_detail', pk=self.object.id)
                
        context = self.get_context_data(object=self.object)
        if 'material_upload' in request.POST:
            context['material_form'] = material_form
        else:
            context['consulta_form'] = form
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
        
        # Agendamentos futuros
        context['agendamentos'] = self.request.user.paciente_perfil.agendamentos.filter(status='A').order_by('data_hora')
        
        datas = [c.data_hora.strftime("%d/%m") for c in reversed(consultas)]
        notas = [c.desempenho_nota for c in reversed(consultas)]
        context['chart_labels'] = datas
        context['chart_data'] = notas
        
        return context

class ExportarProntuarioPDFView(LoginRequiredMixin, FonoaudiologoRequiredMixin, View):
    def get(self, request, pk, *args, **kwargs):
        paciente = get_object_or_404(Paciente, pk=pk, fonoaudiologo=request.user.fonoaudiologo)
        consultas = paciente.consultas.all().order_by('-data_hora')
        
        context = {
            'paciente': paciente,
            'consultas': consultas,
        }
        pdf = render_to_pdf('clinica/pdfs/relatorio_evolucao.html', context)
        if pdf:
            response = HttpResponse(pdf, content_type='application/pdf')
            filename = f"Relatorio_{paciente.nome.replace(' ', '_')}.pdf"
            content = "attachment; filename=%s" % filename
            response['Content-Disposition'] = content
            return response
        return HttpResponse("Not found")

class GerarAtividadePDFView(LoginRequiredMixin, FonoaudiologoRequiredMixin, View):
    def get(self, request, pk, *args, **kwargs):
        paciente = get_object_or_404(Paciente, pk=pk, fonoaudiologo=request.user.fonoaudiologo)
        form = GerarAtividadeForm()
        return render(request, 'clinica/gerar_atividade.html', {'form': form, 'paciente': paciente})

    def post(self, request, pk, *args, **kwargs):
        paciente = get_object_or_404(Paciente, pk=pk, fonoaudiologo=request.user.fonoaudiologo)
        form = GerarAtividadeForm(request.POST)
        
        if form.is_valid():
            titulo = form.cleaned_data['titulo']
            conteudo = form.cleaned_data['conteudo_atividade']
            
            context = {
                'paciente': paciente,
                'fono': request.user.fonoaudiologo,
                'conteudo': conteudo,
            }
            pdf = render_to_pdf('clinica/pdfs/atividade_personalizada.html', context)
            
            if pdf:
                # O pdf retornado por render_to_pdf é uma HttpResponse. O conteúdo binário está em pdf.content
                file_name = f"atividade_{paciente.nome.replace(' ', '_')}.pdf"
                
                # Salvar no banco
                novo_material = MaterialDidatico(
                    paciente=paciente,
                    titulo=titulo,
                    descricao="Gerado automaticamente via sistema."
                )
                novo_material.arquivo.save(file_name, ContentFile(pdf.content))
                novo_material.save()
                
                return redirect('paciente_detail', pk=paciente.id)
                
        return render(request, 'clinica/gerar_atividade.html', {'form': form, 'paciente': paciente})

class CadastroFonoView(View):
    def get(self, request):
        form = FonoaudiologoCadastroForm()
        return render(request, 'clinica/cadastro_fono.html', {'form': form})

    def post(self, request):
        form = FonoaudiologoCadastroForm(request.POST)
        if form.is_valid():
            # Criar User
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                email=form.cleaned_data['email']
            )
            # Criar Fono
            fono = form.save(commit=False)
            fono.user = user
            fono.save()
            return redirect('login')
        return render(request, 'clinica/cadastro_fono.html', {'form': form})

class CadastroPacienteView(View):
    def get(self, request):
        form = PacienteCadastroForm()
        return render(request, 'clinica/cadastro_paciente.html', {'form': form})

    def post(self, request):
        form = PacienteCadastroForm(request.POST)
        if form.is_valid():
            # Criar User
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['nome']
            )
            # Criar Paciente
            paciente = form.save(commit=False)
            paciente.user = user
            paciente.save()
            return redirect('login')
        return render(request, 'clinica/cadastro_paciente.html', {'form': form})

class AgendamentoUpdateView(LoginRequiredMixin, FonoaudiologoRequiredMixin, UpdateView):
    model = Agendamento
    form_class = AgendamentoForm
    template_name = 'clinica/agendamento_form.html'
    success_url = reverse_lazy('dashboard_fono')

    def get_queryset(self):
        return Agendamento.objects.filter(fonoaudiologo=self.request.user.fonoaudiologo)

class AgendamentoDeleteView(LoginRequiredMixin, FonoaudiologoRequiredMixin, DeleteView):
    model = Agendamento
    template_name = 'clinica/agendamento_confirm_delete.html'
    success_url = reverse_lazy('dashboard_fono')

    def get_queryset(self):
        return Agendamento.objects.filter(fonoaudiologo=self.request.user.fonoaudiologo)
