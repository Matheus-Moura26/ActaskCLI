# Actask CLI

CLI oficial do Actask para uso humano e por agentes de IA.

> Status: **v1.0.0 preparada localmente**. A tag e a release privada ainda devem ser publicadas pelo orquestrador.

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

## Instalacao

Cada pessoa deve instalar e autenticar sua propria copia. A CLI armazena a sessao individualmente no cofre do sistema operacional; nunca compartilhe arquivos de configuracao ou credenciais.

### Binario da release

Depois que `v1.0.0` for publicada, baixe o arquivo correspondente na pagina de Releases privada do GitHub:

| Sistema | Arquivo |
| --- | --- |
| Windows x64 | `actask-windows-x64.exe` |
| Linux x64 | `actask-linux-x64` |
| macOS Intel | `actask-macos-x64` |
| macOS Apple Silicon | `actask-macos-arm64` |

No Linux e macOS, conceda permissao de execucao e mova o binario para um diretorio no `PATH`:

```bash
chmod +x actask-linux-x64
sudo mv actask-linux-x64 /usr/local/bin/actask
actask version
```

No Windows, mantenha `actask-windows-x64.exe` em um diretorio incluido no `PATH`, ou execute-o diretamente:

```powershell
.\actask-windows-x64.exe version
```

### Verificacao do download

Baixe tambem `SHA256SUMS` da mesma release. No Linux, verifique o arquivo baixado assim:

```bash
grep ' actask-linux-x64$' SHA256SUMS | sha256sum -c -
```

No macOS:

```bash
grep ' actask-macos-arm64$' SHA256SUMS | shasum -a 256 -c -
```

No Windows, compare o hash exibido com a linha correspondente em `SHA256SUMS`:

```powershell
Get-FileHash .\actask-windows-x64.exe -Algorithm SHA256
```

Nao execute um binario cujo SHA-256 nao corresponda ao checksum publicado.

### pipx

Usuarios com acesso SSH ao repositorio privado podem instalar diretamente pela tag:

```bash
pipx install "git+ssh://git@github.com/Matheus-Moura26/ActaskCLI.git@v1.0.0"
actask version
```

### Clone para desenvolvimento

```bash
git clone git@github.com:Matheus-Moura26/ActaskCLI.git
cd ActaskCLI
git checkout v1.0.0
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
actask version
```

No Windows, ative o ambiente com `.\.venv\Scripts\Activate.ps1`. Para validar a instalacao de desenvolvimento, execute `python -m ruff check .`, `python -m mypy`, `python -m pytest` e `python -m build`.

## Primeiro acesso

```bash
actask login
actask whoami
```

`login` solicita senha sem eco no terminal. A autorizacao de cada comando continua sendo decidida pelo backend; um `403` significa que a conta autenticada nao possui permissao para aquela operacao.
