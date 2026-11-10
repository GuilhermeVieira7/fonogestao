from django.core.management.base import BaseCommand
from clinica.models import TermoVersao


TERMOS_USO = """TERMOS DE USO – FonoGestão Clínica
Versão 1.0 | Vigência: Junho de 2026

1. ACEITAÇÃO DOS TERMOS
Ao utilizar a plataforma FonoGestão Clínica ("Plataforma"), você declara que leu, compreendeu e concorda com os presentes Termos de Uso. Caso não concorde, não utilize a Plataforma.

2. DESCRIÇÃO DO SERVIÇO
A FonoGestão é uma plataforma de gestão clínica voltada para fonoaudiólogos e seus pacientes. Permite o cadastro de pacientes, registro de consultas, agendamentos, envio de materiais didáticos e geração de relatórios.

3. CADASTRO E ACESSO
3.1. Para utilizar a Plataforma, é necessário criar uma conta com informações verdadeiras, completas e atualizadas.
3.2. Você é responsável pela confidencialidade de suas credenciais de acesso.
3.3. Qualquer atividade realizada com suas credenciais é de sua responsabilidade exclusiva.

4. USO PERMITIDO
4.1. A Plataforma destina-se exclusivamente ao uso por profissionais de fonoaudiologia devidamente habilitados e seus pacientes.
4.2. É proibido usar a Plataforma para fins ilegais, fraudulentos ou que violem direitos de terceiros.
4.3. O usuário compromete-se a não compartilhar informações de pacientes fora do contexto clínico autorizado.

5. RESPONSABILIDADES DO PROFISSIONAL
5.1. O fonoaudiólogo é o único responsável pelo conteúdo clínico inserido na Plataforma, incluindo diagnósticos, planos de tratamento e evoluções.
5.2. O uso da Plataforma não substitui o julgamento clínico profissional.

6. PROPRIEDADE INTELECTUAL
Todo o conteúdo da Plataforma, incluindo interface, código-fonte, logotipos e textos, é protegido por direitos autorais. É vedada a reprodução sem autorização prévia.

7. LIMITAÇÃO DE RESPONSABILIDADE
A FonoGestão não se responsabiliza por danos decorrentes de uso indevido da Plataforma, falhas de conectividade ou acesso não autorizado causado por negligência do usuário.

8. ALTERAÇÕES NOS TERMOS
Estes Termos podem ser atualizados periodicamente. O usuário será notificado sobre alterações relevantes e deverá aceitar a nova versão para continuar usando a Plataforma.

9. CONTATO
Para dúvidas sobre estes Termos, entre em contato através do administrador da plataforma ou pelo e-mail de suporte.

10. LEI APLICÁVEL
Estes Termos são regidos pela legislação brasileira, em especial pelo Marco Civil da Internet (Lei 12.965/2014) e pelo Código de Defesa do Consumidor (Lei 8.078/1990)."""


POLITICA_PRIVACIDADE = """POLÍTICA DE PRIVACIDADE E PROTEÇÃO DE DADOS – FonoGestão Clínica
Versão 1.0 | Vigência: Junho de 2026

1. INTRODUÇÃO
A FonoGestão Clínica está comprometida com a proteção dos dados pessoais de seus usuários, em conformidade com a Lei Geral de Proteção de Dados Pessoais (LGPD – Lei nº 13.709/2018).

2. DADOS COLETADOS
Coletamos os seguintes dados para operação da Plataforma:
- Dados de identificação: nome completo, CPF, data de nascimento;
- Dados de contato: e-mail, telefone;
- Dados clínicos: histórico de consultas, materiais, planos de tratamento (exclusivamente para pacientes vinculados ao profissional);
- Dados de acesso: endereço IP, data e hora de login e aceite de termos.

3. FINALIDADE DO TRATAMENTO
Os dados são tratados para:
a) Gerenciar o cadastro de pacientes e profissionais;
b) Registrar e acompanhar consultas e evoluções clínicas;
c) Enviar materiais didáticos e atividades;
d) Cumprir obrigações legais e regulatórias;
e) Garantir a segurança da plataforma.

4. BASE LEGAL (Art. 7º e Art. 11 da LGPD)
O tratamento de dados é fundamentado em:
- Consentimento do titular (Art. 7º, I);
- Execução de contrato (Art. 7º, V);
- Cumprimento de obrigação legal (Art. 7º, II);
- Tutela da saúde (Art. 11, II, f), para dados sensíveis de saúde.

5. COMPARTILHAMENTO DE DADOS
Os dados NÃO são vendidos ou compartilhados com terceiros para fins comerciais. Podem ser compartilhados apenas:
- Com o próprio profissional de fonoaudiologia responsável pelo paciente;
- Em cumprimento de obrigação legal ou ordem judicial.

6. ARMAZENAMENTO E SEGURANÇA
Os dados são armazenados em ambiente seguro com acesso restrito. Adotamos medidas técnicas e organizacionais para proteger os dados contra acessos não autorizados, perdas ou destruição.

7. RETENÇÃO DE DADOS
Os dados são mantidos pelo período necessário para cumprimento das finalidades e pelo prazo mínimo exigido pela legislação de saúde vigente (5 anos, conforme CFM e CFFa).

8. DIREITOS DO TITULAR
Nos termos da LGPD, você tem direito a:
- Confirmar a existência de tratamento;
- Acessar seus dados;
- Corrigir dados incompletos ou desatualizados;
- Solicitar anonimização, bloqueio ou eliminação de dados desnecessários;
- Revogar o consentimento a qualquer momento;
- Peticionar à ANPD (Autoridade Nacional de Proteção de Dados).

9. COOKIES
A Plataforma utiliza cookies de sessão estritamente necessários para o funcionamento. Não utilizamos cookies de rastreamento ou publicidade.

10. ENCARREGADO DE DADOS (DPO)
Para exercer seus direitos ou esclarecer dúvidas, entre em contato com o administrador responsável da clínica ou acesse o painel de suporte.

11. ALTERAÇÕES NESTA POLÍTICA
Esta Política pode ser atualizada. O usuário será notificado e deverá aceitar a nova versão para continuar utilizando a Plataforma."""


LGPD_CONSENTIMENTO = """TERMO DE CONSENTIMENTO PARA TRATAMENTO DE DADOS PESSOAIS (LGPD)
Versão 1.0 | Vigência: Junho de 2026

Ao aceitar este termo, você, como titular dos dados ou responsável legal, concede o CONSENTIMENTO LIVRE, INFORMADO E INEQUÍVOCO para o tratamento dos seus dados pessoais pela plataforma FonoGestão Clínica, nos termos do Art. 7º, inciso I, da Lei Geral de Proteção de Dados (LGPD – Lei nº 13.709/2018).

DADOS TRATADOS:
- Dados pessoais de identificação (nome, CPF, data de nascimento);
- Dados de contato (e-mail, telefone);
- Dados de saúde e histórico clínico fonoaudiológico (dados sensíveis, tratados com base no Art. 11, II, f da LGPD).

FINALIDADE:
Os dados são coletados para gestão da relação clínica entre o profissional fonoaudiólogo e o paciente, incluindo agendamentos, registros de consultas, envio de materiais e acompanhamento de evolução.

RESPONSÁVEL PELO TRATAMENTO (CONTROLADOR):
O profissional fonoaudiólogo cadastrado na Plataforma é o controlador dos dados de seus pacientes. A plataforma FonoGestão atua como operadora.

PRAZO DE RETENÇÃO:
Os dados serão mantidos pelo período de vigência do tratamento clínico e pelo prazo legal mínimo de 5 (cinco) anos após o encerramento do tratamento, conforme normas do Conselho Federal de Fonoaudiologia (CFFa).

REVOGAÇÃO DO CONSENTIMENTO:
Você pode revogar este consentimento a qualquer momento, solicitando ao profissional responsável ou ao administrador da plataforma. A revogação não afeta o tratamento realizado anteriormente.

SEUS DIREITOS:
Você tem direito a acessar, corrigir, eliminar e portar seus dados, conforme os Art. 17 a 22 da LGPD. Para exercê-los, entre em contato com o responsável pela clínica.

Ao clicar em "Li e Aceito todos os Termos", você confirma que:
1. Leu e compreendeu este termo de consentimento;
2. Concorda com o tratamento dos seus dados pessoais conforme descrito acima;
3. Tem ciência dos seus direitos como titular de dados."""


class Command(BaseCommand):
    help = 'Popula os Termos de Uso, Política de Privacidade e Consentimento LGPD padrão.'

    def handle(self, *args, **options):
        termos = [
            {'tipo': 'uso', 'versao': '1.0', 'conteudo': TERMOS_USO},
            {'tipo': 'privacidade', 'versao': '1.0', 'conteudo': POLITICA_PRIVACIDADE},
            {'tipo': 'lgpd', 'versao': '1.0', 'conteudo': LGPD_CONSENTIMENTO},
        ]
        for t in termos:
            obj, created = TermoVersao.objects.get_or_create(
                tipo=t['tipo'],
                versao=t['versao'],
                defaults={'conteudo': t['conteudo'], 'ativo': True},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Criado: {obj.get_tipo_display()} v{obj.versao}"))
            else:
                self.stdout.write(self.style.WARNING(f"Já existe: {obj.get_tipo_display()} v{obj.versao}"))
