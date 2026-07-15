# Seguranca

## Origem oficial

O repositorio oficial da Actask CLI e Skill e:

`https://github.com/Matheus-Moura26/ActaskCLI`

Baixe binarios somente das Releases desse repositorio. Antes de executar um binario, compare seu SHA-256 com o arquivo `SHA256SUMS` publicado na mesma release. Forks podem ser usados para leitura e contribuicao, mas nao sao uma fonte confiavel de binarios oficiais.

## Credenciais e relatos

Nao envie credenciais, senhas, tokens de sessao, cabecalhos de autenticacao, dumps ou respostas reais da API em issues, pull requests, logs ou exemplos. Se um segredo for exposto, revogue-o primeiro e comunique o incidente por um canal privado ao mantenedor; nao abra uma issue publica com o valor.

Cada usuario deve executar `actask login` diretamente. A Skill e agentes que a utilizam nunca devem solicitar ou receber a senha ou token do usuario.

## Limite de seguranca

A CLI nao concede permissoes. O ActaskBack autentica e autoriza novamente cada requisicao, inclusive quando ela nao veio desta CLI. Protecoes de login, politicas de sessao, rate limiting e controles do ambiente de producao pertencem ao ActaskBack e nao podem ser implementados somente neste repositorio.

## Dependencias e publicacao

As GitHub Actions sao fixadas por commit SHA, o workflow usa menor privilegio e as releases incluem checksums. Dependabot acompanha dependencias Python e Actions. Secret scanning, push protection e alertas de vulnerabilidade devem permanecer habilitados nas configuracoes do GitHub.
