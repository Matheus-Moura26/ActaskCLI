# Hardening da distribuicao publica da Actask CLI e Skill

## Objetivo

Permitir que a CLI e a Skill sejam mantidas em repositorio publico sem publicar credenciais, induzir instalacoes de origem falsa ou conceder permissoes desnecessarias aos workflows. Esta feature nao altera o ActaskBack, seus endpoints, sua autenticacao ou seus deploys.

## Requisitos

- **PUB-001:** Documentar o repositorio GitHub oficial e exigir que binarios sejam obtidos somente de releases desse repositorio.
- **PUB-002:** Documentar e testar a verificacao do `SHA256SUMS` antes da execucao de um binario baixado.
- **PUB-003:** Manter credenciais, tokens e respostas reais fora de exemplos, fixtures, logs e commits; valores de teste devem ser marcadores inequivocamente ficticios.
- **PUB-004:** Fixar GitHub Actions por SHA completo e manter referencia legivel da versao na mesma linha.
- **PUB-005:** Aplicar menor privilegio aos workflows: leitura por padrao e escrita de conteudo somente no job que cria a release.
- **PUB-006:** Executar Dependabot para dependencias Python e GitHub Actions e habilitar alertas/correcoes de seguranca suportados pelo GitHub.
- **PUB-007:** A Skill deve recusar credenciais e orientar instalacao/verificacao exclusivamente pela origem oficial.
- **PUB-008:** Registrar separadamente os controles que dependem do ActaskBack e nao representa-los como concluidos nesta feature.

## Criterios de aceitacao

- Os testes falham se Actions voltarem a referencias mutaveis ou se a permissao global voltar a `contents: write`.
- Os testes falham se README/Skill deixarem de indicar a origem oficial ou a verificacao de checksum.
- A suite completa, lint, tipos e build passam sem alteracao no ActaskBack.
- O diff desta feature esta integralmente contido no repositorio ActaskCLI.

## Fora de escopo e trabalho futuro

### ActaskBack

- Rate limiting e protecao contra tentativas repetidas em login.
- Revisao de expiracao, revogacao e auditoria das sessoes.
- Testes de autorizacao e abuso executados contra o backend real de cada ambiente.
- Qualquer mudanca de endpoint, banco, autenticacao, storage ou deploy.

### Promocao segura de ambientes

Sera especificada em uma feature posterior, apos investigar as diferencas reais entre `dev`, `stage` e `main`. Ela deve cobrir promocao `dev -> stage -> main`, contratos e testes entre branches, idempotencia, rollback, backups aprovados, compatibilidade de banco/storage e diferencas de hospedagem (Vercel em main e servidor/Nginx em stage). O plano ainda nao pode ser considerado completo sem mapear portas, processos e eventual Cloudflare Tunnel no servidor.

