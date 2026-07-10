# Actask CLI v1 Tasks

**Status:** Draft
**Target:** v1.0.0

## Execution Protocol

Um orquestrador de IA deve executar uma fase por vez e uma tarefa por commit. Testes pertencem a mesma tarefa do comportamento. Nenhuma tarefa e concluida sem seu gate. Apos T14, um agente diferente executa a verificacao independente da especificacao.

## Execution Map

```text
T01 -> T02 -> T03 -> T04
                    |
                    +-> T05 -> T06 -> T07
                    |
                    +-> T08 -> T09 -> T10
                                      |
                                      v
T11 -> T12 -------------------------> T13 -> T14 -> Verify
```

## Phase 1 - Security Contract

### T01 - Inventory backend routes and authorization [x]

**Deliverable:** Matriz das rotas necessarias para a v1 com autenticacao, permissao, associacao ao projeto e respostas esperadas.
**Repositories:** `ActaskCLI`, leitura de `ActaskBack`.
**Depends on:** None.
**Tests:** Nenhum codigo; evidencias por rota e referencias de arquivo.
**Gate:** Toda rota de CLI-001 a CLI-016 possui classificacao; gaps viram tarefas no backend.
**Commit:** `docs: map v1 API authorization contract`

### T02 - Close backend authorization gaps [x]

**Deliverable:** Correcoes minimas no `ActaskBack` para garantir `401`, `403` e filtro por projeto em todas as rotas da v1.
**Repositories:** `ActaskBack`; atualizar referencias no `ActaskCLI`.
**Depends on:** T01.
**Tests:** Integracao por rota: permitido, nao associado, sem permissao e nao autenticado.
**Gate:** Suite do backend passa e chamadas diretas nao contornam autorizacao.
**Commit:** Um commit atomico por gap no backend; um commit documental de sincronizacao na CLI.

### T03 - Define and verify API contracts [x]

**Deliverable:** Fixtures sanitizadas e testes de contrato para login, identidade, projetos e tasks.
**Depends on:** T02.
**Tests:** Contract tests validam campos, paginacao, erros e compatibilidade.
**Gate:** Contratos passam contra servidor simulado e ambiente controlado.
**Commit:** `test: define Actask API contracts`

## Phase 2 - CLI Foundation

### T04 - Scaffold Python package and quality gates [x]

**Deliverable:** `pyproject.toml`, pacote Typer, Ruff, mypy, pytest e CI basica.
**Depends on:** T03.
**Tests:** Smoke test de `actask --help` e `actask version`.
**Gate:** lint, type-check, testes e build local passam.
**Commit:** `build: scaffold Actask CLI package`

### T05 - Implement profiles and secure credentials [x]

**Deliverable:** Perfis de servidor e adapter de keychain sem fallback em texto puro.
**Depends on:** T04.
**Tests:** Unitarios com keychain falso, isolamento por servidor/usuario e redacao de segredos.
**Gate:** AC-01 e CLI-002 passam.
**Commit:** `feat(auth): add secure credential profiles`

### T06 - Implement typed HTTP client [x]

**Deliverable:** Cliente HTTPX com timeout, TLS, headers, erros tipados e request ID.
**Depends on:** T05.
**Tests:** Unitarios e integracao simulando sucesso, timeout, `401`, `403`, `404`, `409` e `5xx`.
**Gate:** Codigos de saida do spec sao preservados.
**Commit:** `feat(client): add typed Actask API client`

### T07 - Implement authentication commands [x]

**Deliverable:** `login`, `logout` e `whoami`.
**Depends on:** T06.
**Tests:** Prompt oculto, sessao valida, revogada e logout; nenhuma credencial em captura de saida.
**Gate:** CLI-001 a CLI-005 e AC-04 passam.
**Commit:** `feat(auth): add login logout and whoami`

## Phase 3 - Domain Commands

### T08 - Implement project commands [x]

**Deliverable:** `projects list` e `projects show`.
**Depends on:** T07.
**Tests:** Saida humana/JSON, paginacao e acesso negado.
**Gate:** CLI-011, CLI-012 e AC-05 passam.
**Commit:** `feat(projects): add read commands`

### T09 - Implement task read commands

**Deliverable:** `tasks list` e `tasks show`, com filtros e paginacao.
**Depends on:** T08.
**Tests:** Projeto permitido, projeto alheio, ID alheio, filtros e paginas.
**Gate:** CLI-013, CLI-014, AC-02, AC-03 e AC-05 passam.
**Commit:** `feat(tasks): add read commands`

### T10 - Implement task write commands

**Deliverable:** `tasks create` e `tasks update` com validacao, confirmacao e `--dry-run`.
**Depends on:** T09.
**Tests:** Sucesso, payload invalido, proibido, conflito, cancelamento e dry-run sem mutacao.
**Gate:** CLI-015, CLI-016 e AC-06 passam.
**Commit:** `feat(tasks): add guarded write commands`

## Phase 4 - AI Skill

### T11 - Initialize the actask-cli Skill

**Deliverable:** Skill criada em `skills/actask-cli/` com o inicializador oficial, `SKILL.md`, `agents/openai.yaml` e `references/commands.md`.
**Depends on:** T09; comandos de leitura devem estar estaveis.
**Tests:** Validador oficial da Skill passa.
**Gate:** Nome, frontmatter, descricao de gatilho e metadados sao validos.
**Commit:** `feat(skill): initialize Actask CLI skill`

### T12 - Add AI safety workflows and forward tests

**Deliverable:** Fluxos de leitura e escrita segura, exemplos JSON e cenarios de forward test.
**Depends on:** T10, T11.
**Tests:** Agente sem contexto previo conclui leitura autorizada e para em `401`, `403`, ambiguidade e acao destrutiva.
**Gate:** CLI-020 a CLI-022 e AC-07 passam sem vazamento de credenciais.
**Commit:** `test(skill): verify guarded AI workflows`

## Phase 5 - Distribution

### T13 - Build multiplatform binaries

**Deliverable:** Pipeline para Windows x64, Linux x64, macOS x64/arm64 e checksums SHA-256.
**Depends on:** T10, T12.
**Tests:** Smoke test de cada binario em runner nativo.
**Gate:** CLI-023, CLI-024 e AC-08 passam.
**Commit:** `ci: build signed v1 release artifacts`

### T14 - Document installation and release v1.0.0

**Deliverable:** Instrucoes de download, verificacao, instalacao, `git clone`, desenvolvimento e release notes.
**Depends on:** T13.
**Tests:** Comandos de instalacao verificados em ambiente limpo.
**Gate:** Tag `v1.0.0`, artefatos e checksums publicados; repositorio permanece privado.
**Commit:** `docs: prepare v1.0.0 release`

## Coverage Matrix

| Layer | Required tests | Expectation |
| --- | --- | --- |
| Credential/config | Unit | Todos os branches e redacao de segredos |
| HTTP client | Unit + integration | Todos os status e falhas de rede do spec |
| Commands | Unit + integration | Caminho feliz, entrada invalida e erros de autorizacao |
| Backend routes in scope | Integration | Autorizado, sem associacao, sem permissao e sem sessao |
| Skill | Validation + forward test | Leitura, escrita segura e paradas obrigatorias |
| Release artifacts | E2E smoke | Cada plataforma suportada |

## Independent Verification

O verificador final deve reconstruir a matriz entre CLI-001..026, AC-01..08, testes e evidencias. Deve executar os gates a partir de checkout limpo, testar chamadas diretas ao backend e procurar segredos em logs, fixtures, historico Git e artefatos. Qualquer criterio sem evidencia objetiva falha a release.
