# PréCalc+

Projeto acadêmico de apoio a Pré-Cálculo e Funções. Etapas 1 a 5 implementadas: início público, login Google por django-allauth, área protegida, fatoração, equações do primeiro grau e equações do segundo grau (Bhaskara) com conteúdo, prática guiada em dois passos, histórico e progresso individual. Fator comum, diferença de quadrados, equações do 1º e 2º grau estão disponíveis; os demais temas continuam em breve.

## Ambiente e execução

Validado no Windows/PowerShell com Python 3.12.14, Django 5.2.18 (LTS) e django-allauth 65.19.7 e python-dotenv 1.2.4. Python 3.12 é compatível com ambos. Não há AGENTS.md nem configuração de lint/tipos no projeto. Nenhuma dependência foi atualizada na etapa 2. O Python do sistema não estava no PATH; foi utilizado o runtime do Codex:

```powershell
& 'C:\Users\marce\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload
```

Com Python instalado normalmente, use `python -m venv .venv` no primeiro comando. Abra **http://127.0.0.1:8000/**. O ambiente virtual já foi criado nesta entrega.

## Configuração Google — login real confirmado pelo usuário

Preparação local confirmada em 12/10/2026: Python 3.12.14, Django 5.2.18 e django-allauth 65.19.7, sem atualização de dependências. As credenciais estavam ausentes na inspeção inicial. A pedido do usuário, as settings agora carregam explicitamente `BASE_DIR / ".env"` antes de ler as configurações, com `python-dotenv==1.2.4`, `override=False` e suporte a BOM UTF-8 do Windows. Variáveis já definidas no ambiente, mesmo vazias, têm prioridade. A dependência evita implementar um parser próprio para comentários, aspas e escapes. O arquivo local foi criado com a chave Django gerada sem exibição e o Client ID informado pelo usuário. O usuário preencheu depois o Client Secret localmente; os três campos estão preenchidos e sem placeholders conhecidos na checagem atual; `DJANGO_ALLOWED_HOSTS=127.0.0.1`. Somente presença e placeholders são verificados, sem exibir valores. A única fonte escolhida é `SOCIALACCOUNT_PROVIDERS["google"]["APP"]`, preenchida pelas variáveis de ambiente; o banco principal não possui SocialApp Google cadastrado.

O servidor principal identificado usa `manage.py runserver 127.0.0.1:8000 --noreload`. Alterar variáveis em outra janela não altera o ambiente desse processo já iniciado; as credenciais precisam estar no processo que inicia o servidor. Não reinicie serviços indiscriminadamente.

Configure o Google em passos:

1. Abra o [Google Cloud Console](https://console.cloud.google.com/) e crie ou selecione um projeto para o PréCalc+.
2. Em **Google Auth Platform → Branding**, configure o nome PréCalc+, seu e-mail de suporte e o contato solicitado. Se a configuração inicial pedir concordância com políticas, leia e conclua pessoalmente.
3. Em **Audience**, use **External** para uma conta Google pessoal. **Internal** só atende contas da organização Google Workspace associada ao projeto. Para esta validação local, mantenha o aplicativo em Testing. Adicione seu e-mail em Test users se o Console exigir; a [documentação de público do Google](https://support.google.com/cloud/answer/15549945) informa uma exceção à lista de usuários de teste para aplicativos que solicitam somente identificação básica.
4. Em **Data Access**, mantenha somente identificação por perfil e e-mail: `.../auth/userinfo.profile` e `.../auth/userinfo.email` (correspondem a `profile` e `email` solicitados pelo allauth). Não adicione escopos de Drive, Gmail, contatos ou acesso offline. O provedor instalado solicita `profile` e `email`; o README anterior afirmava incorretamente que `openid` era acrescentado automaticamente. A biblioteca aceita ID token quando retornado e usa o endpoint de identidade quando ele não é retornado.
5. Em **Clients → Create client**, escolha **Web application**. Cadastre em **Authorized redirect URIs** exatamente **`http://127.0.0.1:8000/accounts/google/login/callback/`**, incluindo a barra final. **Authorized JavaScript origins deve ficar vazio**: este fluxo ocorre no servidor Django e não usa login JavaScript/One Tap. A URI de redirecionamento inclui o caminho do callback; uma origem JavaScript contém somente esquema, host e porta, e é outra configuração.
6. Obtenha o Client ID e o Client Secret e insira-os somente localmente. Não envie o segredo na conversa, não o coloque no código, em logs ou no Git. Não cadastre também um SocialApp no admin.

### Configuração local por .env

Abra `C:\acex 2\.env` em um editor local e preencha somente os valores reais. A chave Django já foi gerada e o Client ID informado foi inserido. `GOOGLE_CLIENT_SECRET` já foi preenchido localmente pelo usuário para o cliente Web criado. Não use textos `COLE_...`, não envie o segredo na conversa e mantenha `DJANGO_ALLOWED_HOSTS=127.0.0.1` e `DJANGO_DEBUG=True` para este ambiente local. `.env` e suas variantes estão no `.gitignore`; `.env.example` continua versionável, com campos vazios.

O arquivo não será sobrescrito por alterações futuras das settings. Se algum valor estiver definido na janela PowerShell, ele prevalece sobre o arquivo; configure-o corretamente ou remova somente essa variável da janela para usar o valor do `.env`. Não é necessário cadastrar novamente o cliente Google.

Depois de preencher, encerre somente o servidor identificado do PréCalc+ (Ctrl+C na janela que o iniciou), e execute:

```powershell
Set-Location 'C:\acex 2'
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload
```

Se o servidor tiver sido iniciado pelo assistente, avise que o arquivo está preenchido para que ele encerre e reinicie somente esse processo. Alterar o `.env` exige reiniciar o servidor: o processo atual com `--noreload` ainda conserva as configurações anteriores. A chave Django persistida no arquivo será usada nos próximos inícios; trocar uma chave anteriormente efêmera invalida sessões antigas, mas preserva usuários e exercícios no banco.

Sem as duas credenciais Google, o site inicia e informa configuração pendente; acesso direto aos endpoints Google responde 503. Sem chave Django, o desenvolvimento usa uma chave efêmera, e reiniciar invalida sessões. Fora do desenvolvimento (`DJANGO_DEBUG=false`), uma chave é obrigatória e cookies exigem HTTPS. Este projeto não inclui hospedagem.

O allauth cria a conta no primeiro acesso e reutiliza a identidade Google nos seguintes. Início de OAuth e logout usam POST com CSRF. O allauth valida state, identidade e destinos de retorno; PKCE está habilitado. Não há vinculação automática por e-mail ou armazenamento de tokens. Uma colisão de e-mail solicita conclusão de cadastro, sem entrar na conta existente.

### Estado da validação real

Após a confirmação de preenchimento pelo usuário, o carregamento do `.env` foi conferido somente por presença e detecção de placeholders, sem imprimir valores. `GOOGLE_CONFIGURED=True`, hosts restritos a `127.0.0.1`, PKCE mantido e nenhum SocialApp Google duplicado no banco. O processo anterior do projeto na porta 8000 (PID 23720) foi identificado pelo executável e comando antes de ser encerrado; somente ele foi reiniciado para carregar o arquivo local. A página `/accounts/login/` respondeu e exibiu o botão Google habilitado. Os logs de acesso com query strings OAuth foram desabilitados somente no lançamento local desse servidor, para não exibir códigos ou tokens de retorno; a configuração da aplicação e seus controles de segurança permanecem intactos.

A primeira execução da suíte com credenciais preenchidas encontrou uma falha em `test_public_pages_and_pending_configuration`: esse teste pressupunha credenciais ausentes. A correção foi restringir o cenário com `@override_settings(GOOGLE_CONFIGURED=False)`. Nenhum teste foi removido ou ignorado, e o código de autenticação não foi alterado. Os três testes de páginas afetados e a suíte completa passaram depois: 26 testes; Django check sem problemas e nenhuma migration pendente.

Login real com Google confirmado pelo usuário no pedido da etapa 4. Conferência do banco principal: um aluno persistido, uma identidade Google vinculada, nome disponível e nenhuma identidade Google duplicada. O usuário informou que ainda não verificou uma questão, o progresso, logout e novo login com persistência. Esses passos continuam pendentes; não foram marcados como concluídos por testes com mocks. A substituição posterior da chave OAuth exige atualizar somente o `.env` local e reiniciar o servidor identificado. Usuários e exercícios reais de teste não são apagados automaticamente.

Depois da configuração, usar sempre `http://127.0.0.1:8000/`:

1. Cancelar um início de login e verificar a mensagem, sem sessão autenticada.
2. Entrar com Google, confirmar criação do aluno, nome e acesso privado.
3. Sair pelo botão e confirmar que a área do aluno volta ao login.
4. Entrar outra vez e conferir que a mesma identidade Google reutiliza o usuário.
5. Resolver uma questão, conferir histórico e progresso, sair e entrar novamente para verificar a persistência.

O primeiro login foi confirmado pelo usuário; os demais passos acima continuam pendentes de observação ou confirmação manual. Após acrescentar o carregamento do `.env`, os dois testes de configuração e a suíte completa passaram: **26 testes**, incluindo os 24 anteriores. Os testes novos verificam carregamento antes da leitura das settings (incluindo BOM e aspas) e prioridade do ambiente, inclusive valores vazios. Django check sem problemas, nenhuma migration pendente e dependências sem conflitos. O código de autenticação não foi alterado, nenhuma conta foi criada e o SQLite principal foi preservado. Usuário e exercícios criados na validação real serão dados reais de teste, mantidos no banco; não serão apagados automaticamente.

## Equações do primeiro grau — etapa 4

Abra **Área do aluno → Estudar equações → Praticar equações**. O conteúdo explica igualdade, a mesma operação nos dois lados, isolamento de x e verificação por substituição. A prática usa o mesmo fluxo, registro de tentativas e proteção contra reenvio/concorrência da fatoração; nenhuma dependência foi acrescentada.

Geramos a de −5 a 5 (exceto zero), b de −10 a 10 e solução x de −9 a 9; depois calculamos c = a × x + b (de −55 a 55). Coeficientes ±1 são exibidos como x e −x, e constantes negativas com subtração. No passo 1, informe apenas c − b, de −45 a 45; no passo 2, apenas x, de −9 a 9. Ambos os campos aceitam inteiros com até 6 caracteres. Respostas positivas, negativas e zero são válidas quando corretas. O gabarito não vem do navegador; é calculado a partir de a, b e c persistidos.

Exemplo: **3x + 6 = 18**. Subtraia 6 dos dois lados: **3x = 12** (resposta 12). Divida ambos os lados por 3: **x = 4** (resposta 4). Confira: **3 × 4 + 6 = 18**. A resposta futura e a conferência só são apresentadas no momento adequado. Dicas de sinal/operação descrevem relações numéricas identificáveis; outros erros recebem orientação neutra.

Na área do aluno, **Todos / Fatoração / Equações** filtra juntos o progresso e o histórico. Os critérios de conclusão, primeira tentativa e consulta permanecem iguais aos da etapa 2. O total geral usa a soma dos acertos na primeira tentativa dividida pela soma das concluídas, não a média de percentuais dos módulos. Sem concluídas, há estado vazio.

`core/equations.py` contém somente geração, notação, correção e explicação das equações. `core/views.py`, `core/forms.py` e os templates reaproveitam o fluxo existente com ramificações explícitas para o novo tipo; não há framework genérico de exercícios. A página `/praticar/` serve os dois módulos; o endereço antigo `/fatoracao/praticar/` continua atendido.

A migration `core.0002_linear_equations` acrescenta c opcional, permite a e b com sinal e adapta a restrição de parâmetros conforme o tipo. Registros de fatoração mantêm c vazio e os parâmetros, tentativas, datas e significado anteriores. Antes de aplicá-la no principal, as operações foram revisadas e foi criado backup consistente em `backups/precalc-before-equations-20261012-a6e913fa.sqlite3` (pasta ignorada pelo Git). Depois da aplicação, aluno, identidade Google, tokens e colunas antigas dos exercícios foram comparados ao estado anterior sem alterações; a integridade do SQLite retornou ok.

Validação da etapa 4: **38 testes aprovados**, incluindo os 26 anteriores, os 3.990 conjuntos possíveis de parâmetros da geração, sinais/zero, formato, dicas, campos inválidos, passos, consulta, reenvio, isolamento, CSRF, progresso por módulo/geral, migração de um registro antigo e concorrência. Django check sem problemas e nenhuma migration pendente. Lint/tipos não estão configurados.

No banco visual isolado `C:\Users\marce\AppData\Local\Temp\precalc-equations-visual-x0gqqjv1\visual.sqlite3`, com usuário e cookies próprios, foram conferidos: conteúdo em computador; equação com coeficiente negativo e solução zero; erro de operação, nova tentativa e conclusão; no celular, entrada inválida com erro acessível, erro de sinal, solução negativa, consulta, próxima questão, filtros e progresso. Fator comum também foi concluído novamente nesse ambiente. O logout isolado bloqueou o conteúdo privado. As telas medidas em 1280 × 900 e 390 × 844 não excederam a largura da viewport. O navegador reutilizava CSS antigo e ocultava Todos no celular; a URL da folha foi versionada com `?v=4`, e os três filtros foram conferidos visíveis. Algumas capturas falharam temporariamente; as imagens efetivamente obtidas foram usadas para inspeção, sem atribuir inspeção visual a uma captura que falhou.

O banco visual e o backup foram preservados, e seu servidor foi encerrado. O principal permanece em `127.0.0.1:8000` com o módulo disponível. Login real inicial é confirmação do usuário; os testes OAuth continuam usando mocks. Questão/progresso/logout/novo login na conta Google real e cancelamento real continuam pendentes. Nenhum outro conteúdo foi implementado.

## Equações do segundo grau (Bhaskara) — etapa 5

Abra **Área do aluno → Eq. 2º grau → Praticar Bhaskara**. O conteúdo explica o discriminante Δ = b² − 4ac, a fórmula de Bhaskara e verificação por substituição. A prática segue o mesmo fluxo de dois passos dos módulos anteriores: passo 1 pede Δ, passo 2 pede as duas raízes inteiras x₁ e x₂ (a ordem não importa).

Geramos a ∈ {−3,…,−1,1,…,3}, raízes x₁ e x₂ ∈ [−6,6], depois calculamos b = −a(x₁+x₂) e c = a·x₁·x₂; isso garante Δ = b²−4ac sempre quadrado perfeito e raízes inteiras. Delta é recalculado no servidor a partir de a, b, c — não armazenado. Coeficientes ±1 são exibidos como x e −x; constantes e coeficientes negativos usam o sinal menos tipográfico. Os campos aceitam inteiros com até 6 caracteres; step 1 de 0 a 5000, step 2 de −6 a 6.

Exemplo: **2x² − 7x + 3 = 0**. Passo 1: Δ = (−7)² − 4·2·3 = 49 − 24 = **25**. Passo 2: x = (7 ± 5) ÷ 4 → x₁ = **½** (fora do escopo da prática), mas com raízes inteiras garantidas, por ex. **x² − 5x + 6 = 0**: Δ = 1, x₁ = 2, x₂ = 3.

A migration `core.0003_quadratic` acrescenta QUADRATIC às escolhas e adapta a restrição de parâmetros (a de −3 a 3, b de −36 a 36, c de −108 a 108, a ≠ 0). Registros anteriores não são alterados. Execute `manage.py migrate` antes de usar o módulo.

Arquivos novos: `core/quadratic.py` (geração, expressão, raízes, verificação, dicas), `core/migrations/0003_quadratic.py`, `templates/core/quadratic_content.html`, `core/tests/test_quadratic.py` (testes unitários) e `core/tests/test_quadratic_flow.py` (testes de fluxo HTTP e concorrência).

Validação da etapa 5: **60+ testes** (38 anteriores + 20 unitários de quadratic.py + testes de fluxo HTTP), incluindo geração com 200 amostras aleatórias, raízes ordenadas com a negativo, type-safety das respostas JSON, fluxo de dois passos, consulta, isolamento, CSRF, progresso por módulo, concorrência. Django check sem problemas; aplicar migration antes de rodar.

## Como usar a fatoração

Depois de entrar, abra **Área do aluno → Estudar fatoração → Praticar**. Escolha um dos dois tipos e gere uma questão. Cada questão tem dois passos; o servidor valida o passo atual e só apresenta o seguinte depois de um acerto. Respostas erradas permanecem preenchidas e recebem uma dica; entradas inválidas mostram erros junto aos campos. O botão **Ver resolução** encerra a questão como consulta, sem crédito de acerto. Depois, use **Próxima questão** ou consulte o histórico na área do aluno. Questões em andamento podem ser retomadas na prática e no histórico.

As respostas são números inteiros com até 6 caracteres, sem expressões livres:

- Fator comum: coeficientes positivos até 30 e MDC maior que 1. Primeiro informe o **maior** fator comum; depois os dois coeficientes dos parênteses (valores de 1 a 30).
- Diferença de quadrados: raízes geradas de 2 a 9. Primeiro informe a raiz positiva (campo de 1 a 9); depois dois números com sinais, de −9 a 9, no formato `(x + número)(x + número)`. A ordem dos fatores é equivalente.

Exemplos completos: `6x + 9` → passo 1: `3` → passo 2: `2` e `3` → `3(2x + 3)`. Para `x² − 9` → passo 1: `3` → passo 2: `-3` e `3` (ou `3` e `-3`) → `(x − 3)(x + 3)`. São fatorações de expressões, não resolução de equações. Não há interpretador algébrico, IA ou biblioteca simbólica.

## Critérios do progresso

- **Concluídas:** questões encerradas ao acertar os dois passos ou consultar a resolução; questões em andamento ficam fora do denominador.
- **Corretas na primeira tentativa:** exatamente um envio correto por passo, sem consulta. Entradas inválidas também contam como tentativas.
- **Aproveitamento na primeira tentativa:** corretas na primeira tentativa ÷ concluídas × 100. Se não houver concluídas, o site mostra um estado vazio.
- **Resoluções consultadas:** encerramentos por consulta, identificados separadamente no histórico; não são acertos do aluno.

O histórico mostra as 10 questões mais recentes da própria conta. O banco preserva todos os registros.

## Estrutura e decisões

- `config/settings.py` e `config/urls.py`: configurações convencionais, SQLite, segurança, allauth e rotas protegidas. A autenticação da etapa 1 foi mantida.
- `core/equations.py` e `core/test_equations.py`: matemática do primeiro grau e seus testes, incluindo migração e concorrência.
- `core/factoring.py`: geração, correção e dicas em funções Python; MDC com `math.gcd` e raízes com `math.isqrt`. O gabarito é calculado a partir dos parâmetros do banco.
- `core/models.py` e `core/migrations/0001_initial.py`: um modelo `Exercise` guarda proprietário, tipo, parâmetros (a, b e c quando equação), passo, revisão, tentativas, consulta e datas. Acerto na primeira tentativa e progresso são calculados, não duplicados em campos.
- `core/forms.py`: validação nativa Django de escolhas, inteiros, intervalos e tamanho; erros associados aos campos por `aria-describedby`.
- `core/views.py`: páginas, filtro por usuário da sessão e POST seguido de redirecionamento. Uma chave de criação única por aluno evita gerar duas questões ao reenviar o mesmo formulário. Um único UPDATE condicionado à revisão atual salva tentativas e estado juntos, impedindo duas submissões de vencerem. `select_for_update` não bloquearia linhas no SQLite.
- `templates/` e `static/core/style.css`: apresentação e identidade compartilhadas, com foco visível e layout responsivo; nenhuma regra de correção no navegador ou JavaScript acrescentado.
- `core/test_settings.py`: carregamento do arquivo local e precedência das variáveis de ambiente.
- `core/tests.py`: oito testes da etapa 1. `core/test_factoring.py`: matemática, formulários, fluxo, isolamento, reenvio, progresso, acessibilidade e concorrência com duas threads.
- `manage.py`, `config/asgi.py` e `config/wsgi.py`: inicialização e comandos gerados pelo Django.

Os blocos seguem requisitos do projeto e convenções Django. A comparação de revisões é uma decisão própria para o fluxo no SQLite, não um motor genérico de tutoria. Entradas abusivas rejeitadas são armazenadas com limite de 64 caracteres; respostas dentro do formato são preservadas integralmente.

## Validação e estado real — 12/10/2026

```powershell
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py showmigrations
.\.venv\Scripts\python.exe manage.py migrate --plan
.\.venv\Scripts\python.exe -m pip check
```

Estado inicial confirmado nos arquivos e execução: 23 testes aprovados, Django check sem problemas, sem migrations pendentes. A retomada corrigiu a associação do erro numérico ao campo para leitores de tela e acrescentou um teste de regressão; **24 testes aprovados** na suíte final, incluindo os oito anteriores. Lint e checagem de tipos não estão configurados.

A migration `core.0001_initial` cria somente o modelo Exercise, com restrições de unicidade, passo, conclusão e parâmetros positivos. Ela já estava aplicada no banco principal `C:\acex 2\db.sqlite3`, conforme o registro de migrations e a existência da tabela; não foi reaplicada. `PRAGMA integrity_check` retornou `ok`. O banco principal foi preservado byte a byte (SHA-256 comparado antes e depois), sem contas de teste. Antes de aplicar qualquer migration futura, confira suas operações e faça um backup do SQLite com a [API de backup do Python](https://docs.python.org/3.12/library/sqlite3.html#sqlite3.Connection.backup).

A conferência visual retomou o banco isolado identificado em `C:\Users\marce\AppData\Local\Temp\precalc-visual-53kic0d7\visual.sqlite3`. As duas questões anteriores foram preservadas e foi feito backup em `visual-before-resume-20261012.sqlite3` nessa mesma pasta antes de retomar os testes. Nenhum processo antigo estava ativo nas portas 8000/8001. O servidor de teste foi iniciado apenas em `127.0.0.1:8001`, autenticando a conta de teste já existente pelo admin normal do Django. Isso não cria uma rota de bypass nem adiciona usuário no banco principal. Ao final, o servidor isolado foi encerrado; o banco e seu backup foram mantidos.

Conferidos no navegador em computador (1280 × 900) e celular (390 × 844): conteúdo, escolha e geração dos dois tipos, campos, resposta correta/incorreta, dicas, novas tentativas, consulta à resolução, conclusão, próxima questão, histórico, progresso e navegação. A largura do conteúdo não excedeu a viewport nas telas verificadas. O foco visível e a associação dos erros também foram inspecionados. Atualizar o progresso e a questão consultada manteve os registros idênticos: 7 questões e 16 envios no banco de teste. O progresso final de teste foi 1 acerto na primeira tentativa em 7 concluídas (14,3%), com 2 consultas. Logout encerrou a sessão e voltar à área privada redirecionou ao login.

Os testes OAuth simulam a troca de token e a identidade externa, mantendo o processamento e persistência do allauth. **Mocks e login local no banco isolado não comprovam autenticação real com Google.** O login inicial real foi posteriormente confirmado pelo usuário; segundo acesso, saída e persistência do progresso real ainda aguardam validação manual. Os outros conteúdos, Moodle e hospedagem estão fora desta etapa.

## Referências oficiais

- [Django 5.2: compatibilidade Python](https://docs.djangoproject.com/en/5.2/releases/5.2/) e [versões suportadas](https://www.djangoproject.com/download/).
- [Requisitos allauth](https://docs.allauth.org/en/latest/installation/requirements.html), [configuração social](https://docs.allauth.org/en/latest/socialaccount/configuration.html) e [credenciais por settings](https://docs.allauth.org/en/latest/socialaccount/provider_configuration.html).
- [Google no allauth](https://docs.allauth.org/en/latest/socialaccount/providers/google.html) e [OAuth web do Google](https://developers.google.com/identity/protocols/oauth2/web-server).

A configuração de scopes, acesso online e PKCE adapta o exemplo oficial do provedor Google (django-allauth, licença MIT), usando credenciais de ambiente em vez de cadastro administrativo. A interface, as views de configuração pendente e os testes são código deste projeto, não exemplos atribuídos à documentação.

Fontes da etapa 2: [Forms](https://docs.djangoproject.com/en/5.2/topics/forms/), [erros e acessibilidade dos campos](https://docs.djangoproject.com/en/5.2/ref/forms/api/#django.forms.BoundField.aria_describedby), [models](https://docs.djangoproject.com/en/5.2/topics/db/models/), [UPDATE e limitações de bloqueio](https://docs.djangoproject.com/en/5.2/ref/models/querysets/), [sessões](https://docs.djangoproject.com/en/5.2/topics/http/sessions/), [autenticação](https://docs.djangoproject.com/en/5.2/topics/auth/default/), [testes](https://docs.djangoproject.com/en/5.2/topics/testing/overview/) e [migrations](https://docs.djangoproject.com/en/5.2/topics/migrations/). O módulo é código próprio; estas fontes fundamentam o uso dos recursos do framework.

Carregamento local: [documentação oficial do python-dotenv](https://bbc2.github.io/python-dotenv/). Usa o caminho explícito do projeto e `override=False`; não procura configurações em pastas superiores.
