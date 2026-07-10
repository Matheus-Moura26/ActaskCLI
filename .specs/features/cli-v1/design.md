# Actask CLI v1 Design

## Architecture

```text
Human or AI agent
        |
        v
 Typer commands
        |
        +--> input/output adapters (table, JSON, prompts)
        |
        v
 application services
        |
        +--> credential store (OS keychain)
        |
        v
 typed HTTP client -----> ActaskBack -----> authorization + database
```

## Proposed Modules

```text
src/actask_cli/
  __init__.py
  main.py
  commands/
    auth.py
    projects.py
    tasks.py
  client/
    api.py
    errors.py
    models.py
  config/
    profiles.py
    credentials.py
  output/
    console.py
    json_output.py
  safety/
    confirmation.py
tests/
  unit/
  integration/
  contract/
skills/
  actask-cli/
    SKILL.md
    agents/openai.yaml
    references/commands.md
```

## Authentication Flow

1. O usuario seleciona ou informa um perfil de servidor.
2. `login` le email e senha por prompt oculto.
3. A CLI chama `POST /auth/login` por HTTPS.
4. A resposta e validada e a sessao e salva no keychain, usando servidor + usuario como chave.
5. Requisicoes seguintes recuperam a sessao em memoria apenas durante o processo e enviam `X-Session-Token`.
6. `401` marca a credencial como invalida e orienta novo login; a CLI nao tenta usar credencial de outro usuario.

## Authorization Boundary

O backend e a unica autoridade. Antes de cada comando entrar na v1, o orquestrador deve localizar a rota usada e provar por teste que:

- usuario associado e com permissao recebe sucesso;
- usuario autenticado sem associacao ou permissao recebe `403`;
- usuario sem sessao valida recebe `401`;
- consultas por ID nao vazam existencia ou conteudo indevido;
- listagens filtram no banco, em vez de buscar tudo e filtrar na CLI.

Gaps encontrados devem ser corrigidos e testados no `ActaskBack` antes de liberar o comando correspondente.

## API Compatibility

A v1 pode consumir o contrato atual, mas deve manter modelos de transporte isolados da apresentacao. Alteracoes de API devem ser coordenadas com `ActaskBack`, preferencialmente sob rotas versionadas ou com testes de contrato publicados.

## Credential Storage

Usar `keyring` com Windows Credential Manager, macOS Keychain e Secret Service no Linux. Configuracoes nao secretas, como URL e usuario ativo, ficam em arquivo local com permissoes restritas. Nunca oferecer fallback silencioso para token em texto puro.

## Output Contract

Modo humano usa tabelas compactas e mensagens acionaveis. `--json` usa um envelope estavel:

```json
{
  "data": {},
  "meta": {"request_id": null},
  "error": null
}
```

Erros mantem `data` nulo e incluem um codigo publico estavel, uma mensagem e detalhes nao sensiveis.

## Skill Design

A Skill `actask-cli` sera inicializada com a ferramenta oficial de criacao de Skills e mantida pequena. O `SKILL.md` contem o fluxo e os guardrails; `references/commands.md` contem o catalogo de comandos e schemas. A Skill deve:

- confirmar identidade com `actask whoami --json`;
- descobrir IDs por listagem, sem inventa-los;
- usar `--json` para leitura e parsing;
- usar `--dry-run` antes de escrita quando disponivel;
- interromper em `401` e devolver o login ao usuario;
- interromper em `403`, sem tentar contornar autorizacao;
- evitar exclusoes e outras acoes destrutivas por padrao.

## Testing Strategy

- Unitarios para parsing, perfis, keychain, erros, serializacao e confirmacoes.
- Integracao com servidor HTTP simulado para contratos de requisicao e resposta.
- Contrato contra ambiente controlado do Actask para `401`, `403`, filtros e CRUD autorizado.
- E2E dos binarios em Windows, Linux e macOS.
- Forward test da Skill com um agente sem contexto previo e credenciais ficticias.

## Release

Tags semanticas `vX.Y.Z` acionam CI. O pipeline executa lint, type-check, testes, build multiplataforma, smoke tests e publicacao de artefatos com SHA-256. A primeira release funcional sera `v1.0.0`.
