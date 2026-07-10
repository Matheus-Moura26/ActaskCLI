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
