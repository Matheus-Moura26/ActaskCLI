# Actask CLI State

## Decisions

### AD-001 - Repositorio independente e privado (substituida por AD-008)

**Decision:** A CLI vive em `ActaskCLI`, separada de `ActaskBack` e `ActaskFront`, com visibilidade privada.

**Reason:** Permitir ciclo de release, distribuicao, testes e contribuicoes independentes sem acoplar o produto aos deploys da API ou SPA.

### AD-008 - Repositorio publico com distribuicao endurecida

**Decision:** A CLI e a Skill podem ser publicas porque nao contem a autoridade de acesso. A distribuicao deve identificar a origem oficial, publicar checksums, fixar Actions por SHA, operar com menor privilegio e manter secret scanning e alertas de dependencias habilitados.

**Reason:** O backend continua autenticando e autorizando cada requisicao, enquanto os controles do repositorio reduzem riscos de vazamento acidental e supply chain. Rate limiting e politicas de sessao dependem do ActaskBack e nao fazem parte desta decisao.

### AD-002 - Python com Typer

**Decision:** Implementar a v1 em Python 3.12 com Typer e cliente HTTP baseado em HTTPX.

**Reason:** Boa portabilidade, tipagem, testes simples e empacotamento em executaveis multiplataforma.

### AD-003 - Backend como autoridade

**Decision:** Toda autorizacao e validada pelo backend em cada requisicao. Verificacoes locais servem apenas para experiencia de uso.

### AD-004 - Credencial individual e segura

**Decision:** Armazenar a credencial por perfil de servidor e usuario no cofre do sistema operacional. Nao aceitar token em argumento de linha de comando.

### AD-005 - Automacao orientada a JSON

**Decision:** Todo comando de dados da v1 deve suportar `--json`, codigos de saida estaveis e ausencia de prompts quando executado com flags explicitas.

### AD-006 - Skill acompanha a CLI

**Decision:** A Skill `actask-cli` sera versionada neste repositorio e usara apenas comandos publicos da CLI, sem acesso direto ao banco ou credenciais.

### AD-007 - Identidade estruturada para agentes

**Decision:** `actask whoami` suporta `--json` com o mesmo envelope estavel dos demais comandos de dados.

**Reason:** A Skill precisa confirmar a identidade corrente antes de descobrir ou alterar recursos sem depender de parsing da saida humana.

### AD-009 - Movimentacao usa a rota especializada

**Decision:** `actask tasks update --column-id` chama `PATCH /tasks/{id}/move` com as revisoes esperadas da coluna de origem e destino e uma colocacao protegida por `position` ou `append_to_end`. A CLI consulta apenas a task e as colunas autorizadas para montar esse payload. Sem `--position`, a task e inserida no fim; com `--position`, usa indice base-zero na coluna destino. A CLI recusa combinar a movimentacao com outras atualizacoes na mesma chamada.

**Reason:** A rota especializada registra historico, worklog, transicoes de status e valida concorrencia enquanto o backend resolve a ordem sob seus locks. Recusar a combinacao evita que uma atualizacao via `PUT` seja persistida se o movimento posterior falhar. Nenhuma alteracao no backend e necessaria para este fluxo.

### AD-010 - Detalhe de projeto usa a rota de leitura versionada

**Decision:** `actask projects show` usa `GET /task-loading/v1/projects/{project_id}`. HTTP 405 permanece no codigo de saida 7, mas e apresentado como incompatibilidade de contrato da API, nao como falha interna generica.

**Reason:** A rota generica `/projects/{project_id}` nao oferece GET no backend publicado; a rota versionada aplica o controle de acesso e entrega o `ProjectOut` esperado pela CLI.

### AD-011 - Guardrail local de responsabilidade para escritas da CLI

**Decision:** Antes de `actask tasks update`, a CLI consulta a identidade atual e a task. A operacao prossegue somente quando `assignee_id` e nulo ou corresponde ao usuario autenticado; caso contrario, encerra com codigo 4 e a mensagem `Você não é o responsável desta task`. A mesma verificacao cobre movimentacao porque ela usa o mesmo comando.

**Reason:** A MMS-139 solicitou uma protecao de experiencia de uso exclusivamente na CLI. O backend continua sendo a autoridade final e nao foi alterado; portanto, esta verificacao nao substitui autorizacao server-side nem pretende proteger outros clientes.

### AD-012 - Operacoes de casos pela CLI usando o contrato existente

**Decision:** Expor `tasks cases list`, `tasks cases fields`, `tasks cases create` e `tasks cases update`. A listagem de casos reutiliza o `GET /tasks/{task_id}` autorizado, enquanto campos, criacao e edicao usam `GET /projects/{project_id}/case-fields`, `POST /tasks/{task_id}/cases` e `PUT /tasks/{task_id}/cases/{case_id}`. Valores de campos personalizados sao recebidos como objeto JSON indexado pelo ID da definicao e validados localmente contra tipo e opcoes antes da escrita; o backend continua sendo a autoridade de permissao e persistencia.

**Reason:** O backend publicado ja possui as rotas de casos e de definicoes de campos, evitando uma alteracao de contrato ou migration. A validacao local torna erros de tipo e de opcao acionaveis sem substituir a autorizacao server-side. A mesma verificacao de responsabilidade da CLI e aplicada antes de criar ou editar um caso.

### AD-013 - Comentarios e mencoes pela CLI usam o contrato existente

**Decision:** Expor `tasks comments list` e `tasks comments create`. A listagem usa `GET /tasks/{task_id}/comments`; a criacao usa `POST /tasks/{task_id}/comments` com `content`, `mentioned_user_ids` repetiveis via `--mention-user-id` e `parent_id` opcional. O texto continua podendo conter mencoes `@label`, resolvidas pelo backend.

**Reason:** O backend publicado ja persiste comentarios, replies e notificacoes de mencao. A CLI apenas normaliza o payload, oferece `--dry-run --json`, aplica o guardrail local de responsabilidade antes da escrita e deixa a autorizacao e a resolucao final de usuarios no backend.

## Validation Remediation

### 2026-07-10 - AC-05, AC-06 e evidencia direta de autorizacao

- Adicionados testes de equivalencia semantica entre saida humana e JSON para `whoami`, `projects show` e `tasks show`.
- Adicionado teste de `tasks update --dry-run --json` que valida o payload normalizado e falha se a CLI tentar construir cliente de rede.
- Provisionado `C:\Users\Acdev\RiderProjects\ActaskBack\.venv` apenas com dependencias locais necessarias (`requirements.txt`, `pytest` e `httpx`) para executar `tests/test_cli_v1_authorization.py`.
- Execucao direta no backend concluida com sucesso: `6 passed` em `tests/test_cli_v1_authorization.py`.

### 2026-08-03 - MMS-139 guardrail de responsavel

- Adicionada verificacao previa de responsabilidade em `tasks update`, incluindo movimentacao/ordenacao.
- Tasks sem responsavel e tasks atribuidas ao usuario autenticado continuam permitidas.
- Tasks atribuidas a outra pessoa sao bloqueadas antes de qualquer escrita, com codigo 4 e mensagem definida.
- `pytest -q`: `73 passed`; Ruff e mypy sem erros.

### 2026-08-07 - MMS-150 casos pela CLI

- Adicionados `tasks cases list`, `tasks cases fields`, `tasks cases create` e `tasks cases update` usando as rotas existentes do backend.
- Criacao e edicao reutilizam o guardrail de responsabilidade da task, exigem confirmacao ou `--yes` e oferecem `--dry-run --json`.
- Campos `text`, `number`, `select_single` e `select_multi` sao validados contra as definicoes e opcoes do projeto antes da escrita.
- `pytest -q`: `89 passed`; Ruff, mypy e `git diff --check` sem erros.

### 2026-08-11 - MMS-161 comentarios e mencoes pela CLI

- Adicionados `tasks comments list` e `tasks comments create`, com replies via `--parent-id` e multiplas mencoes via `--mention-user-id`.
- A criacao aplica `--dry-run --json`, confirmacao/`--yes` e o guardrail de responsabilidade antes do `POST`.
- O cliente tipado cobre `GET/POST /tasks/{task_id}/comments`; `@label` continua suportado pelo contrato server-side.
- `pytest -q`: `86 passed`; Ruff, mypy, build e `git diff --check` devem permanecer sem erros antes do push para stage.

## Handoff

- **Feature**: `.specs/features/cli-v1`
- **Phase / Task**: MMS-161 — CLI comments and mentions
- **Completed**: `tasks update` uses the protected stage movement contract; the CLI lists and edits cases with typed custom-field validation and lists/creates task comments with replies and explicit mentions. Existing-task writes read responsibility before sending the backend request.
- **In-progress** (file:line): none
- **Next step**: Independent verification, then release the CLI when authorized.
- **Blockers**: none.
- **Uncommitted files**: none after recording the release evidence.
- **Branch**: `codex/mms161-cli-comments-stage`
