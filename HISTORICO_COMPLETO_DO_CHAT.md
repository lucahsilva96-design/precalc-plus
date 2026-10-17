# Histórico consolidado do chat — PréCalc+

> Documento de continuidade criado em 16/10/2026. Ele reúne os pedidos, as decisões, as alterações e as verificações conhecidas desta conversa. Não é uma transcrição literal de cada mensagem de interface; é um registro técnico detalhado e fiel ao trabalho realizado.
>
> **Segurança:** nenhum segredo, token OAuth, chave de sessão ou conteúdo de `.env` é reproduzido aqui. Valores confidenciais recebidos na conversa foram deliberadamente omitidos.

## 1. Projeto, local e limites de escopo

- Diretório de trabalho: `C:\acex 2`.
- Aplicação: Django, PréCalc+, site educacional de apoio a Pré-Cálculo.
- Ambiente principal local: `http://127.0.0.1:8000`.
- Banco principal preservado: `C:\acex 2\db.sqlite3`.
- Etapas abordadas na conversa:
  1. fundação do site e área protegida;
  2. módulo de fatoração;
  3. preparação e validação real de login Google;
  4. módulo de equações do primeiro grau.
- O escopo explicitamente excluído ao final foi: equações do segundo grau, funções, trigonometria, limites, Moodle e publicação.

## 2. Linha do tempo dos pedidos e resultados

### Etapa 1 — fundação do PréCalc+

O pedido inicial descrevia um site educacional simples para Pré-Cálculo. O estado posterior informado e confirmado durante as continuações foi:

- interface responsiva;
- página pública inicial;
- área protegida para aluno autenticado;
- configuração de autenticação Google com `django-allauth`;
- proteção CSRF;
- logout por `POST`;
- sessões e PKCE preservados;
- sem criar acesso alternativo ou bypass de login.

O relatório recebido mencionava oito testes aprovados no início. Esse número não foi usado como prova isolada; as suítes foram executadas novamente nas etapas seguintes.

### Etapa 2 — fatoração

O pedido seguinte solicitou o primeiro módulo de fatoração. O módulo existente foi confirmado como implementado e mantido:

- dois tipos de exercício: fator comum e diferença de quadrados;
- geração de exercícios no servidor;
- resposta guiada em dois passos;
- tentativas, dicas, consulta à resolução;
- histórico individual;
- progresso individual;
- isolamento de dados por aluno;
- proteção de acesso a exercícios de outro aluno;
- prevenção de duplicidade em reenvio/submissão concorrente.

Houve uma migration de etapa anterior, e a conferência visual foi feita em banco isolado. O login Google real continuava pendente naquele ponto.

### Etapa 3 — configuração e login real com Google

O usuário pediu a configuração local e a validação real do fluxo Google, sem exibir segredos e sem alterar indevidamente as políticas de segurança.

#### Inspeção e decisão técnica

Foram conferidos README, configurações, rotas, versões e variáveis. O projeto usa:

- Python 3.12.14;
- Django 5.2.18 LTS;
- `django-allauth` 65.19.7;
- `python-dotenv` 1.2.4.

Foi consultada documentação oficial do Django, do `django-allauth` e do Google antes das decisões de integração. A aplicação já possuía integração adequada; ela não foi reimplementada.

Foi identificado que o projeto precisava carregar o arquivo local `C:\acex 2\.env` de maneira explícita. A alteração mínima adotada foi carregar `BASE_DIR / ".env"` antes das leituras de configuração, usando `override=False`. Isso preserva variáveis já presentes no ambiente do processo. Também houve suporte a BOM UTF-8 comum em arquivos `.env` do Windows.

#### Variáveis e política de segredos

Foram identificadas e utilizadas estas variáveis:

- `DJANGO_SECRET_KEY`;
- `DJANGO_DEBUG`;
- `DJANGO_ALLOWED_HOSTS`;
- `GOOGLE_CLIENT_ID`;
- `GOOGLE_CLIENT_SECRET`.

Os valores foram verificados apenas quanto a preenchimento e placeholders. Nunca foram impressos em comandos, logs, README ou código versionado. O `.env` está ignorado pelo Git. A configuração local manteve `DJANGO_ALLOWED_HOSTS=127.0.0.1` conforme solicitado.

#### Google Cloud e callback

O usuário informou que criou um cliente OAuth do tipo **Aplicação Web** com este callback:

`http://127.0.0.1:8000/accounts/google/login/callback/`

O callback foi confirmado como compatível com a rota do `django-allauth`. Foi explicado que esse valor é uma URI de redirecionamento completa, enquanto **Authorized JavaScript origins** não é usado por esse login que ocorre no servidor Django; por isso não foi solicitada uma origem JavaScript adicional.

Foi mantida uma única fonte de configuração do provedor: `SOCIALACCOUNT_PROVIDERS["google"]["APP"]`, preenchida pelas variáveis de ambiente. O banco principal não continha um `SocialApp` Google duplicado. A política de não conectar automaticamente contas por e-mail foi preservada.

#### Login real

Depois do preenchimento local do `.env`, foi identificado e reiniciado somente o servidor pertencente ao PréCalc+, ligado a `127.0.0.1:8000`. O processo foi iniciado sem autoreload e com o log de acesso silenciado para não registrar parâmetros sensíveis de callback.

O usuário confirmou que conseguiu realizar o login real com Google. Isso é evidência de validação manual real do primeiro login; não é inferido dos mocks. No banco principal foi confirmado o estado compatível com esse login:

- 1 usuário em `auth_user`;
- 1 conta social Google;
- nenhuma identidade Google duplicada;
- nome disponível para exibição.

Permaneceu pendente, no momento da coleta anterior, o ciclo manual completo de resolver questão, sair, entrar novamente e confirmar que o progresso real do usuário persiste. O usuário respondeu explicitamente que ainda não havia feito essa verificação. Não foi declarado como concluído.

### Etapa 4 — equações do primeiro grau

O pedido final foi retomar o estado real, sem duplicação, e concluir somente o módulo de equações do primeiro grau. O código encontrado já continha uma implementação parcial/avançada da etapa e foi completado e validado.

## 3. Estado técnico final conhecido

### Conteúdo de equações

Foi adicionado o conteúdo protegido de equações do primeiro grau no formato `ax + b = c`.

O conteúdo ensina:

1. igualdade como relação entre dois lados;
2. aplicação da mesma operação nos dois lados;
3. remoção do termo constante;
4. isolamento de `x` por divisão pelo coeficiente;
5. conferência por substituição da resposta na equação original.

O exemplo didático incluído é equivalente a:

`3x + 6 = 18` → subtrair 6 → `3x = 12` → dividir por 3 → `x = 4` → verificar `3 × 4 + 6 = 18`.

Também há explicação para sinais negativos e para termo constante zero.

### Geração e correção

O arquivo `core/equations.py` concentra regras diretas de geração, formatação, resolução e correção, sem `eval`, `exec`, IA ou biblioteca simbólica.

Limites implementados:

- coeficiente `a`: inteiro de -5 a 5, exceto zero;
- termo `b`: inteiro de -10 a 10;
- solução `x`: inteiro de -9 a 9;
- `c` calculado por `a*x + b`;
- resultado intermediário `c - b`: de -45 a 45;
- `c`: de -55 a 55.

Portanto, a geração cobre soluções positivas, negativas e zero. A formatação evita formas didaticamente ruins como `1x`, `-1x` e `+ -3`.

Cada exercício segue dois passos:

1. informar `c − b`, após aplicar a operação inversa aos dois lados;
2. informar `x`, após dividir pelo coeficiente.

Respostas incorretas recebem retorno específico quando for possível identificar um erro de sinal/operação. A tentativa continua registrada e permite nova resposta. A resolução pode ser consultada sem receber crédito de acerto.

### Modelos e persistência

`Exercise.Kind` ganhou `LINEAR = "linear"`. O modelo agora armazena `a`, `b` e `c` para uma equação linear, com uma restrição de banco que distingue corretamente:

- exercícios de fatoração: `a >= 1`, `b >= 1`, `c` nulo;
- exercícios lineares: limites acima, `a != 0` e `c` obrigatório.

A expressão do exercício usa a lógica linear quando o tipo é `linear` e mantém a lógica anterior para fatoração. Histórico e progresso continuam ligados ao aluno proprietário.

### Rotas, telas e filtros

Foram disponibilizadas ou preservadas:

- `/equacoes/`: conteúdo de equações, requer login;
- `/praticar/?kind=linear`: prática guiada de equações;
- rotas existentes de geração, questão, resposta, dica e resolução;
- `/fatoracao/praticar/`: compatibilidade com link de prática de fatoração existente.

Na área do aluno, há filtros de histórico e progresso para:

- Todos;
- Fatoração;
- Equações.

Os totais são calculados sobre o recorte selecionado; o filtro não mistura o progresso das duas áreas.

### Migration e banco principal

Foi criada a migration `core/migrations/0002_linear_equations.py`.

Antes de aplicá-la no banco principal, foram revisadas as operações:

1. remoção da restrição antiga de parâmetros;
2. adição da coluna nullable `c`;
3. atualização dos campos/choices `a`, `b` e `kind`;
4. criação da nova restrição de validação.

Foi criado backup consistente do SQLite, via API `Connection.backup()`, em:

`C:\acex 2\backups\precalc-before-equations-20261012-a6e913fa.sqlite3`

O diretório `backups/` foi incluído no `.gitignore`. A integridade do backup e do banco após a migration foi verificada com SQLite. As linhas das tabelas existentes relevantes foram comparadas antes/depois para confirmar preservação. A migration foi aplicada com sucesso; não havia dados de exercícios reais no banco principal nesse momento.

O estado conferido após a aplicação era:

- usuário principal: preservado;
- conta social Google: preservada;
- exercícios principais: 0;
- integridade SQLite: `ok`;
- migration `0002`: aplicada;
- `migrate --plan`: sem operações pendentes.

## 4. Arquivos alterados ou adicionados na etapa 4

| Arquivo | Alteração e justificativa |
| --- | --- |
| `core/equations.py` | Adicionado. Implementa geração, formatação, correção, dicas e resolução das equações sem avaliação dinâmica. |
| `core/models.py` | Adiciona o tipo linear, coluna `c` e restrição de integridade específica. |
| `core/forms.py` | Ajusta rótulos, limites e campos de resposta para a prática linear. |
| `core/views.py` | Geração, resposta guiada, solução, página de conteúdo e filtros de progresso/histórico. |
| `config/urls.py` | Rota de conteúdo das equações, prática genérica e compatibilidade da prática de fatoração. |
| `core/migrations/0002_linear_equations.py` | Evolução persistente e compatível do esquema. |
| `templates/core/equations_content.html` | Novo conteúdo didático. |
| `templates/core/practice.html` | Texto e navegação de prática compartilhada. |
| `templates/core/exercise.html` | Tutor visual de dois passos, dicas, erros e resolução para equações. |
| `templates/core/topics.html` | Link e disponibilidade do novo módulo. |
| `templates/core/student.html` | Filtros de fatoração/equações e métricas por conteúdo. |
| `templates/core/home.html` | Referência à disponibilidade de equações. |
| `templates/base.html` | Rodapé e versionamento do CSS para invalidar cache de estilo. |
| `static/core/style.css` | Estilo dos filtros, com correção de responsividade. |
| `core/test_equations.py` | Testes de matemática, fluxo, isolamento, CSRF, concorrência e migration. |
| `README.md` | Estado real, configuração Google, módulo e validações documentadas. |
| `.gitignore` | Preserva `.env` e ignora backups locais. |

Não há `AGENTS.md` no diretório. Não há configuração de linter ou checador estático de tipos detectada. Também não há repositório Git inicializado nesse diretório, portanto não havia `git status`/diff para listar alterações rastreadas.

## 5. Testes e verificações realmente executados

### Automatizados

Foram executados com `C:\acex 2\.venv\Scripts\python.exe`:

```powershell
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py migrate --plan
```

Resultado final registrado:

- suíte Django: **38 testes aprovados**;
- `manage.py check`: **nenhum problema identificado**;
- `makemigrations --check --dry-run`: **nenhuma alteração de modelo não migrada**;
- `migrate --plan`: **nenhuma migration pendente**.

Os 38 testes abrangem, entre outros:

- todos os valores permitidos de `a`, `b` e `x` na geração linear;
- soluções positivas, negativas e zero;
- respostas corretas e incorretas em ambos os passos;
- tentativas e dicas;
- consulta de solução sem crédito;
- geração não duplicada/replay e ordem de passos;
- acesso anônimo e CSRF;
- isolamento entre dois alunos;
- concorrência na conclusão;
- filtros e progresso separados;
- regressão dos fluxos de fatoração;
- migração de dados de fatoração a partir da migration anterior;
- autenticação simulada em testes existentes.

Os testes de autenticação usam mocks/ambiente de teste quando aplicável. Eles não são apresentados como comprovação do fluxo OAuth real.

### Conferência visual manual em ambiente isolado

Foi utilizado banco separado, nunca o `db.sqlite3` principal, em uma pasta temporária local. A sessão e o cookie CSRF desse ambiente receberam nomes próprios para evitar colisão com o servidor principal.

Fluxos efetivamente conferidos visualmente:

- conteúdo de equações em desktop;
- geração de equação linear com coeficiente e solução negativos;
- erro de operação no primeiro passo;
- tentativa posterior correta;
- solução zero;
- campo inválido textual e mensagem associada ao campo;
- erro de sinal no segundo passo;
- conclusão e exibição da conferência por substituição;
- consulta de resolução sem crédito;
- geração e conclusão de fatoração após as mudanças;
- filtros de progresso para todos, equações e fatoração;
- bloqueio de conteúdo protegido após logout;
- celular em 390 px e 375 px sem rolagem horizontal;
- correção de filtro oculto no celular causada por uma regra CSS pré-existente.

O ambiente visual isolado foi interrompido ao término, sem apagar o seu banco/arquivos. Alguns pedidos de captura de tela falharam na ferramenta de automação, mas o estado das páginas e dos elementos de acessibilidade foi inspecionado diretamente; isso não foi usado para alegar uma captura inexistente.

### Validação real de Google

Confirmado pelo usuário: primeiro login real com Google funcionou. O banco principal confirmou a criação única de usuário e conta social.

Ainda pendente de validação manual real pelo usuário: resolver exercício em sua própria conta, observar o progresso, fazer logout, entrar novamente e confirmar a persistência do mesmo progresso. Não há evidência manual registrada para esse ciclo completo.

## 6. Problemas encontrados e correções

1. **Carregamento local de `.env` não era explícito.**
   - Correção: `python-dotenv` com prioridade para o ambiente do processo (`override=False`).
   - Motivo: usar as credenciais locais sem sobrescrever configuração já fornecida pelo ambiente.

2. **Possível duplicidade de fonte para Google.**
   - Correção: confirmada a fonte única em settings e ausência de `SocialApp` duplicado no banco.
   - Motivo: evitar credenciais conflitantes.

3. **Filtro “Todos” ficava oculto no celular.**
   - Causa: regra móvel existente para o primeiro link de uma navegação também alcançava a nova navegação de filtros.
   - Correção: regra específica para o primeiro link do filtro e versão de URL do CSS atualizada para evitar cache antigo.
   - Verificação: os três filtros apareceram em largura de 375 px; largura de documento e viewport permaneceram iguais.

4. **Necessidade de armazenar o lado direito da equação.**
   - Correção: coluna `c` nullable e migration compatível, acompanhada de backup e restrição condicional.
   - Motivo: persistir a expressão linear sem quebrar os exercícios de fatoração existentes.

Não foram feitas alterações em credenciais OAuth, controles CSRF, PKCE, sessão, política de associação de contas ou banco principal fora da migration revisada.

## 7. Documentação oficial consultada

- Django 5.2: migrations e validação de modelos.
- django-allauth: provedor Google e configuração baseada em settings.
- Google Cloud / Google Auth Platform: público, usuários de teste, cliente OAuth Web e URIs de redirecionamento.

As referências operacionais relevantes foram mantidas no `README.md`.

## 8. Estado atual e próximos passos manuais reais

O módulo de equações do primeiro grau está implementado, migrado e validado por testes e por conferência visual em ambiente isolado. O banco principal foi preservado e possui o login Google real já confirmado pelo usuário.

Para encerrar a validação manual de conta real, resta apenas este roteiro no servidor principal:

1. entrar com a conta Google já usada;
2. abrir Fatoração ou Equações;
3. resolver uma questão até a conclusão;
4. abrir a área do aluno e conferir o novo registro/progresso;
5. sair pelo botão de logout;
6. tentar abrir uma rota protegida e confirmar o redirecionamento ao login;
7. entrar de novo com a mesma conta;
8. confirmar nome e progresso preservados.

Os dados criados nesse roteiro são dados reais de teste do usuário e não devem ser apagados automaticamente.

## 9. Comandos úteis de continuidade

```powershell
Set-Location 'C:\acex 2'
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py migrate --plan
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload
```

Nunca inclua o conteúdo de `.env` em commits, mensagens, relatórios ou arquivos versionados.
