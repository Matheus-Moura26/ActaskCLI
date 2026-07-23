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
