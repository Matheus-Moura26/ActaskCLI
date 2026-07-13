# Actask CLI v1 Specification

**ID:** CLI-V1
**Status:** Draft
**Target:** v1.0.0

## Goal

Entregar uma CLI multiplataforma para usuarios e agentes de IA operarem o Actask com autenticacao individual, autorizacao obrigatoria no backend, saida estruturada e comportamento previsivel.

## Users

- Usuario humano que prefere terminal ou automacao local.
- Agente de IA autorizado pelo mesmo usuario.
- Administrador que instala, audita e diagnostica a CLI.

## Requirements

### Authentication

- **CLI-001:** `actask login` solicita URL, email e senha de forma interativa, sem expor a senha no terminal.
- **CLI-002:** A sessao retornada pelo backend e armazenada no cofre seguro do sistema operacional, separada por servidor e usuario.
- **CLI-003:** `actask logout` invalida a sessao no backend e remove a credencial local.
- **CLI-004:** `actask whoami` valida a sessao no backend e retorna a identidade corrente.
- **CLI-005:** Sessao ausente, expirada ou revogada resulta em mensagem acionavel e codigo de saida estavel, sem revelar a credencial.

### Authorization

- **CLI-006:** Toda requisicao autenticada envia a sessao individual e depende da autorizacao do backend.
- **CLI-007:** Um usuario nao associado a um projeto nao consegue listar, ler, criar ou alterar tasks desse projeto.
- **CLI-008:** Permissoes globais e papeis de projeto sao respeitados nos comandos correspondentes.
- **CLI-009:** Respostas `401` e `403` sao distintas na CLI e nunca convertidas em sucesso ou lista vazia enganosa.
- **CLI-010:** A v1 so libera um comando quando a rota correspondente possui verificacao server-side e testes de acesso permitido e negado.

### Commands

- **CLI-011:** `actask projects list` retorna somente projetos acessiveis.
- **CLI-012:** `actask projects show <id>` retorna um projeto acessivel ou falha com codigo apropriado.
- **CLI-013:** `actask tasks list --project <id>` suporta paginacao, filtros essenciais e nenhum vazamento entre projetos.
- **CLI-014:** `actask tasks show <id>` valida acesso ao projeto da task.
- **CLI-015:** `actask tasks create` e `actask tasks update` validam entrada, oferecem `--dry-run` e respeitam permissoes do backend.
- **CLI-016:** Acoes destrutivas, se adicionadas na v1, exigem confirmacao ou `--yes` e ficam fora da Skill por padrao.

### Automation and AI

- **CLI-017:** Comandos de dados suportam `--json` com envelope estavel: `data`, `meta` e `error`.
- **CLI-018:** A CLI usa stdout para resultados e stderr para diagnosticos.
- **CLI-019:** Codigos de saida distinguem sucesso, entrada invalida, nao autenticado, proibido, nao encontrado, conflito e falha de rede/servidor.
- **CLI-020:** A Skill `actask-cli` ensina descoberta, leitura e alteracao segura usando a CLI, priorizando `--json` e `--dry-run`.
- **CLI-021:** A Skill nunca solicita, imprime, armazena ou compartilha token; login permanece uma acao do usuario.
- **CLI-022:** Antes de escrita, a Skill le o estado atual, apresenta a mudanca pretendida e pede confirmacao quando o pedido nao for explicitamente autorizativo.

### Distribution and Operations

- **CLI-023:** A CLI roda em Windows x64, Linux x64 e macOS arm64/x64.
- **CLI-024:** Releases assinadas ou acompanhadas de checksums sao publicadas a partir de tags `vX.Y.Z`.
- **CLI-025:** Logs e telemetria nao incluem credenciais, headers de autenticacao ou payloads sensiveis.
- **CLI-026:** `actask version` informa versao da CLI e perfil de servidor, sem dados secretos.

## Stable Exit Codes

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 2 | Invalid input or usage |
| 3 | Not authenticated |
| 4 | Forbidden |
| 5 | Not found |
| 6 | Conflict or invalid state |
| 7 | Network or server failure |

## Acceptance Criteria

- **AC-01:** Credenciais nao aparecem em argumentos, stdout, stderr, logs, traces ou fixtures.
- **AC-02:** Usuario sem associacao recebe `403` ao tentar acessar tasks de outro projeto, tanto pela CLI quanto por chamada direta a API.
- **AC-03:** Usuario autorizado consegue listar e ler tasks do projeto.
- **AC-04:** Sessao revogada falha como nao autenticada e pode ser substituida por novo login.
- **AC-05:** Todos os comandos de leitura produzem saida humana e JSON semanticamente equivalentes.
- **AC-06:** Escrita com `--dry-run` nao altera o servidor e informa o payload normalizado.
- **AC-07:** A Skill conclui cenarios de leitura usando apenas a CLI e para com seguranca diante de `401`, `403` ou ambiguidade destrutiva.
- **AC-08:** Binarios da release passam smoke test nos sistemas suportados e seus checksums sao publicados.

## Out of Scope for v1

- Acesso direto ao banco de dados.
- Credenciais compartilhadas, service accounts ou impersonacao.
- Execucao offline com sincronizacao posterior.
- Cobertura integral de todos os recursos da interface web.
- Plugins de terceiros executados dentro do processo da CLI.
- Resolução semântica genérica de nomes humanos para pessoas, campos e opções customizadas; planejada em `cli-semantic-field-resolution`.
