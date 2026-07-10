# Actask CLI State

## Decisions

### AD-001 - Repositorio independente e privado

**Decision:** A CLI vive em `ActaskCLI`, separada de `ActaskBack` e `ActaskFront`, com visibilidade privada.

**Reason:** Permitir ciclo de release, distribuicao, testes e contribuicoes independentes sem acoplar o produto aos deploys da API ou SPA.

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

## Handoff

- **Feature**: `.specs/features/cli-v1`
- **Phase / Task**: Phase 1 / T02 - Close backend authorization gaps
- **Completed**: T01
- **In-progress** (file:line): `app/routes/projects.py:105` and `app/services/task_query.py:857` - implementing documented authorization gaps
- **Next step**: Add the protected project detail route and make explicit inaccessible task queries return `403`, with direct API tests.
- **Blockers**: none
- **Uncommitted files**: `.specs/features/cli-v1/api-authorization-matrix.md`, `.specs/features/cli-v1/tasks.md`, `.specs/STATE.md`
- **Branch**: `main`
