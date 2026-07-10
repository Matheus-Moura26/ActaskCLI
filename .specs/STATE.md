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
- **Phase / Task**: Phase 4 in progress
- **Completed**: T01, T02, T03, T04, T05, T06, T07, T08, T09, T10, T11
- **In-progress** (file:line): none
- **Next step**: Complete Phase 4 / T12 with offline forward tests for the Skill.
- **Blockers**: none
- **Uncommitted files**: none
- **Branch**: `main`
