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

## Validation Remediation

### 2026-07-10 - AC-05, AC-06 e evidencia direta de autorizacao

- Adicionados testes de equivalencia semantica entre saida humana e JSON para `whoami`, `projects show` e `tasks show`.
- Adicionado teste de `tasks update --dry-run --json` que valida o payload normalizado e falha se a CLI tentar construir cliente de rede.
- Provisionado `C:\Users\Acdev\RiderProjects\ActaskBack\.venv` apenas com dependencias locais necessarias (`requirements.txt`, `pytest` e `httpx`) para executar `tests/test_cli_v1_authorization.py`.
- Execucao direta no backend concluida com sucesso: `6 passed` em `tests/test_cli_v1_authorization.py`.

## Handoff

- **Feature**: `.specs/features/public-repository-hardening`
- **Phase / Task**: Fase 1 / T02
- **Completed**: T01, T02, T03, T04, T05, T06, T07, T08, T09, T10, T11, T12, T13, T14
- **In-progress** (file:line): none
- **Next step**: Add executable security requirements, then implement only CLI/Skill changes.
- **Blockers**: none.
- **Uncommitted files**: none after recording the release evidence.
- **Branch**: `codex/harden-public-cli-skill`
