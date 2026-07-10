# Actask CLI

CLI oficial do Actask para uso humano e por agentes de IA.

> Status: **v1 em planejamento**. Este repositorio ainda nao contem uma versao funcional da CLI.

O objetivo da v1 e oferecer login individual, consultas seguras e comandos essenciais de tasks e projetos. Toda autorizacao sera validada pelo backend do Actask; a CLI nunca sera a fonte de verdade para permissoes.

## Escopo da v1

- Login e logout por usuario.
- Credencial armazenada no cofre seguro do sistema operacional.
- Identificacao da sessao com `actask whoami`.
- Listagem apenas de projetos acessiveis ao usuario.
- Listagem e leitura de tasks respeitando associacao ao projeto e permissoes.
- Criacao e atualizacao de tasks com confirmacao e suporte a `--dry-run`.
- Saida humana e estruturada por `--json`.
- Skill `actask-cli` para agentes de IA operarem a CLI com guardrails.
- Binarios para Windows, Linux e macOS, alem de instalacao para desenvolvimento via Git.

## Documentacao para implementacao

- [Especificacao da v1](.specs/features/cli-v1/spec.md)
- [Arquitetura proposta](.specs/features/cli-v1/design.md)
- [Plano de tarefas](.specs/features/cli-v1/tasks.md)
- [Protocolo do orquestrador de IA](docs/AI_ORCHESTRATION.md)
- [Decisoes e estado do projeto](.specs/STATE.md)

## Regra central de seguranca

A CLI pode antecipar indisponibilidade de um comando para melhorar a experiencia, mas cada requisicao deve ser autenticada e autorizada novamente pelo backend. Uma tentativa fora do escopo do usuario deve falhar com `401` ou `403`, inclusive quando chamada diretamente sem a CLI.

## Repositorio

Este projeto e privado. Nao inclua tokens, senhas, arquivos de configuracao pessoais ou respostas reais da API em commits, testes ou exemplos.
