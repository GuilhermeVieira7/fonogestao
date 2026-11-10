# FonoGestão Clínica

Sistema de gestão para clínicas de fonoaudiologia. Permite cadastro de pacientes, agendamentos, consultas, geração de atividades e relatórios em PDF, gerenciamento de clínicas e conformidade com a LGPD.

## Requisitos

- **Python 3.12** (recomendado). Python 3.10 e 3.11 também funcionam.
  > ⚠️ **Não use Python 3.13 ou 3.14**: as versões fixadas de `Pillow` (10.3.0) e `psycopg2-binary` (2.9.9) não instalam nelas e o `pip install` falha.
- pip

No Windows, confira quais versões você tem com `py -0p`. Se não tiver a 3.12, instale com:

```powershell
py install 3.12
```

(ou baixe em https://www.python.org/downloads/)

## Como rodar

Todos os comandos abaixo são executados na **pasta raiz do projeto** (onde fica o `manage.py`).

### 1. Crie o ambiente virtual

**Windows:**
```powershell
py -3.12 -m venv .venv
```

**Linux/Mac:**
```bash
python3.12 -m venv .venv
```

> Se já existir uma pasta `.venv` ou `venv` copiada de outro computador, ela **não funciona** (aponta para o Python daquela máquina). Recrie com `py -3.12 -m venv --clear .venv`.

### 2. Ative o ambiente virtual

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
```

> Se aparecer erro de "execução de scripts desabilitada", rode uma vez:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

**Linux/Mac:**
```bash
source .venv/bin/activate
```

Com o ambiente ativo, `python` passa a ser o Python do projeto. Os próximos comandos assumem isso.

### 3. Instale as dependências

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

Copie o arquivo de exemplo (se ainda não existir um `.env`):

**Windows:**
```powershell
copy .env.example .env
```

**Linux/Mac:**
```bash
cp .env.example .env
```

O `.env` padrão já funciona para desenvolvimento local com SQLite:

```env
SECRET_KEY=sua-chave-secreta-aqui
DEBUG=True

# Opcional: usar PostgreSQL em vez de SQLite
# DATABASE_URL=postgres://usuario:senha@127.0.0.1:5432/nome_do_banco
```

### 5. Aplique as migrações

```bash
python manage.py migrate
```

### 6. Cadastre os Termos de Uso / Privacidade / LGPD

```bash
python manage.py populate_termos
```

Esse passo é obrigatório: sem os termos, o middleware LGPD redireciona todo usuário logado para a tela de aceite. O comando pode ser rodado mais de uma vez sem duplicar nada.

### 7. Crie usuários

**Opção A: dados de teste (mais rápido)**

```bash
python create_test_data.py
```

Cria os usuários abaixo (só os que ainda não existem):

| Usuário    | Senha   | Perfil            |
|------------|---------|-------------------|
| `admin`    | `admin` | Superusuário      |
| `fono`     | `123`   | Fonoaudiólogo     |
| `paciente` | `123`   | Paciente          |

> Use essas senhas só em desenvolvimento.

**Opção B: seu próprio administrador**

```bash
python manage.py createsuperuser
```

### 8. Rode o servidor

```bash
python manage.py runserver
```

| Página           | Endereço                          |
|------------------|-----------------------------------|
| Sistema          | http://127.0.0.1:8000             |
| Login            | http://127.0.0.1:8000/login/      |
| Painel admin     | http://127.0.0.1:8000/admin/      |

Para parar o servidor, pressione `Ctrl+C` no terminal.

---

## Resumo rápido (Windows)

Para quem já fez a instalação uma vez, só é preciso:

```powershell
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

Instalação do zero, em sequência:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py populate_termos
python create_test_data.py
python manage.py runserver
```

---

## Rodando os testes

```bash
python manage.py test clinica
```

---

## Primeiros passos no sistema

1. Entre no admin (`/admin/`) com o superusuário.
2. **Crie um Fonoaudiólogo** vinculando-o a um usuário Django (ou use o cadastro em `/cadastro/fonoaudiologo/`).
3. **Crie clínicas** em `/clinicas/` e vincule fonoaudiólogos.
4. **Cadastre horários de atendimento** em `/disponibilidades/`.
5. **Cadastre pacientes** pelo painel do fonoaudiólogo (`/dashboard/`) ou em `/cadastro/paciente/`.

### Agenda, histórico e feriados

- **Consulta única ou recorrente.** Ao marcar uma consulta, informe o início e o término. Se escolher "Consultas recorrentes" com um período (em dias, meses ou anos, até 2 anos), o sistema cria uma sessão por semana, sempre no mesmo dia da semana e horário.
- **Histórico automático.** Quando o horário de término de uma consulta confirmada passa, ela vai sozinha para o histórico do paciente como "aguardando avaliação". O profissional só registra as observações e o plano de ação, e o paciente vê a sessão depois de avaliada. Também é possível marcar "Paciente faltou".
  - Isso acontece quando alguém abre o painel, o prontuário ou a área do paciente.
  - Para rodar também em um agendador (cron), use `python manage.py gerar_consultas`.
- **Feriados nacionais.** Fixos e móveis: Carnaval, Sexta-feira Santa e Corpus Christi. Eles aparecem na agenda. Para uma sessão em feriado, o paciente pode pedir a remarcação para outro dia da mesma semana, e o profissional aprova ou recusa no painel. Feriados estaduais e municipais não estão incluídos.
- **Anexos.** Na aba Material Didático do prontuário, "Anexar PDF / Mídia" aceita PDFs prontos, imagens, áudios e vídeos de até 25 MB. Desmarque "Disponibilizar para o paciente" para guardar documentos só no prontuário.

---

## Publicar no Render (Blueprint)

O repositório já vem com tudo pronto: `render.yaml` (Blueprint), `build.sh` (build) e Gunicorn + WhiteNoise.

1. Envie o código para o GitHub.
2. No [painel do Render](https://dashboard.render.com), clique em **New > Blueprint** e selecione o repositório.
3. O Render lê o `render.yaml` e cria:
   - o banco **PostgreSQL** `fonogestao-db`;
   - o site **fonogestao** (Python 3.12), com `SECRET_KEY` gerada automaticamente e `DEBUG=False`.
4. Ele pede três valores para o administrador: `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL` e `DJANGO_SUPERUSER_PASSWORD`. O admin é criado no primeiro deploy.
5. Clique em **Apply** e aguarde o build. Ele instala as dependências, roda `collectstatic`, `migrate` e `populate_termos`.
6. Acesse `https://fonogestao.onrender.com` (ou o endereço mostrado pelo Render).

**Observações importantes**

- **Arquivos enviados** (fotos de perfil, materiais e PDFs de atividades): no plano *free* o disco do Render é apagado a cada deploy ou reinício. Para guardá-los de vez, mude o serviço para o plano *starter* e descomente o bloco `disk` e a variável `MEDIA_ROOT` no `render.yaml`.
- **Banco free**: o PostgreSQL gratuito do Render expira após 30 dias. Para uso real, escolha um plano pago do banco.
- **Plano free "dorme"**: após 15 minutos sem acesso, o primeiro acesso seguinte demora cerca de 1 minuto.
- **E-mail de recuperação de senha**: sem SMTP configurado, os e-mails só aparecem nos logs. Para enviar de verdade, defina no Render as variáveis `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` e `DEFAULT_FROM_EMAIL` (veja `.env.example`).
- **Domínio próprio**: adicione-o em `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` (o domínio `.onrender.com` já é liberado automaticamente).

---

## Problemas comuns

| Sintoma | Causa / solução |
|---------|-----------------|
| `Python was not found` ou `No Python at '...python.exe'` | O `.venv` foi criado em outro computador, ou o Python não está no PATH. Use `py -3.12` e recrie o ambiente (passo 1). |
| `Failed to build 'Pillow'` no `pip install` | Você está em Python 3.13/3.14. Instale o 3.12 e recrie o `.venv`. |
| Todo login cai na tela "Aceitar termos" sem conseguir sair | Termos não cadastrados. Rode `python manage.py populate_termos`. |
| `Error: That port is already in use` | Outro servidor está na porta 8000. Feche-o ou use `python manage.py runserver 8001`. |

---

## Estrutura principal

```
manage.py            # Ponto de entrada do Django
create_test_data.py  # Cria usuários de teste
clinica/             # App principal (models, views, forms, URLs, middleware)
  management/        # Comandos customizados (populate_termos)
core/                # Configurações Django (settings, URLs raiz)
templates/           # Todos os templates HTML
static/              # Arquivos estáticos (CSS, JS, imagens)
media/               # Uploads (materiais didáticos, etc.)
```

## Tecnologias

- **Django 5.0.4**: framework web
- **SQLite** (padrão) ou **PostgreSQL** (produção)
- **Bootstrap 5.3** + **Bootstrap Icons 1.11**: interface
- **xhtml2pdf**: geração de PDFs
- **Gunicorn** + **WhiteNoise**: servidor e arquivos estáticos em produção (Render)
- **python-decouple**: variáveis de ambiente
