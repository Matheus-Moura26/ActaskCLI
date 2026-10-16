# Actask CLI v1.2.0

## Alteracoes

- Todo argumento de task (`tasks show`, `update`, `promote`, `comments`, `cases`, `create --parent-id` e `grouping --parent`/`--child`/`children`) aceita a URL web da task (`/tasks/all?task=<task-id>`), alem do ID.
- Novo `actask tasks url <task-id-ou-url> [--json]`, que imprime o link da task.
- O JSON de `tasks show`, `list`, `create`, `update` e `promote` inclui `url`; a saida humana ganha a URL como ultima coluna.
- A URL web e derivada automaticamente para os servidores oficiais; para outros servidores, `actask login` pergunta a `Web URL for task links`.
- A Skill `actask-cli` orienta a passar URLs coladas diretamente para a CLI e a responder pedidos de link com `tasks url`.

## Atualizacao

Instale ou atualize pela tag `v1.2.0`. Perfis existentes continuam validos sem novo login.

---

# Actask CLI v1.1.0

## Alteracoes

- Adicionados `actask tasks grouping candidates`, `group`/`create`, `list`/`log`, `children` e `undo`.
- O agrupamento usa `grouping_parent_id`, mantem os filhos fora do board, preserva a secao **Agrupadas** e registra operacoes auditaveis com undo atomico.
- O cliente HTTP tipado cobre as cinco rotas de agrupamento do backend, com paginacao, `--dry-run`, confirmacao, idempotencia e JSON estavel.
- A Skill `actask-cli` agora explica a diferenca entre agrupamento e subtask, os filtros `isGroupingTask`/`isGroupedTask` e o fluxo seguro de criacao/desfazimento.

## Atualizacao

Instale ou atualize pela tag `v1.1.0`.

---

# Actask CLI v1.0.4

## Alteracoes

- `actask tasks create` agora aceita `--parent-id` para criar subtasks de primeiro nivel.
- A Skill orienta a validar a task pai, usar o mesmo projeto e executar dry-run antes da criacao.

## Atualizacao

Instale ou atualize pela tag `v1.0.4`.

---

# Actask CLI v1.0.3

## Correcoes

- `actask projects show` agora usa a rota de leitura versionada e autorizada do backend.
- HTTP 405 e reportado como incompatibilidade de contrato, sem ser mascarado como erro interno generico.
- Skill atualizada com a orientacao segura para codigo 7 por incompatibilidade de contrato.

## Atualizacao

Instale ou atualize pela tag `v1.0.3`.

---

# Actask CLI v1.0.2

## Alteracoes

- Adicionados `actask projects columns` e `actask projects fields` para descoberta segura da configuracao real de cada projeto.
- A Skill agora desambigua termos como "pendentes" entre coluna e Status configurado, e usa `meta.total` para contagens completas.

## Atualizacao

Instale ou atualize pela tag `v1.0.2`.

---

# Actask CLI v1.0.1

## Alteracoes

- `actask login` usa `https://actaskapi.bluefronte.com` como Server URL padrao.
- Documentada a instalacao operacional global por binario no PATH ou por `pipx`.
- A Skill instrui IAs a usarem uma CLI globalmente disponivel e a reservarem `.venv` para desenvolvimento e testes.

## Atualizacao

Instale ou atualize pela tag `v1.0.1`.

---

# Actask CLI v1.0.0

## Highlights

- Login individual com armazenamento de sessao no cofre do sistema operacional.
- `whoami`, leitura de projetos e leitura de tasks com saida humana ou `--json`.
- Criacao e atualizacao de tasks com validacao, confirmacao, `--yes` e `--dry-run`.
- Skill `actask-cli` para fluxos de IA seguros, usando somente comandos publicos da CLI.
- Binarios nativos para Windows x64, Linux x64, macOS x64 e macOS arm64.

## Security

Cada chamada usa a sessao individual do usuario. A autorizacao e sempre aplicada pelo backend do Actask; a CLI nao concede acesso por conta propria. Respostas `401` e `403` permanecem distintas e nao revelam credenciais.

## Verification

Esta release inclui `SHA256SUMS`. Antes de executar um binario, siga a secao "Verificacao do download" no README e confirme o SHA-256 do arquivo correspondente.

## Upgrade notes

Esta e a primeira versao publica da CLI. Nao ha passos de migracao. A release e criada apenas a partir da tag `v1.0.0` no repositorio privado.
