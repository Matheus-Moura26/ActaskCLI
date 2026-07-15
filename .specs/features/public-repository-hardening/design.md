# Design

## Limite de confianca

O codigo da CLI e da Skill pode ser publico porque nao contem a autoridade de acesso. A identidade e a autorizacao continuam sendo decididas pelo ActaskBack em cada requisicao. A publicacao, entretanto, introduz riscos de supply chain: forks maliciosos, binarios adulterados, dependencias comprometidas e segredos adicionados por engano.

## Controles locais

1. Origem canonica: `https://github.com/Matheus-Moura26/ActaskCLI`.
2. Integridade: cada release publica `SHA256SUMS`; instaladores devem conferir o arquivo antes de executar o binario.
3. Workflows imutaveis: Actions externas sao fixadas por commit SHA.
4. Menor privilegio: CI opera com `contents: read`; apenas o job final de release recebe `contents: write`.
5. Atualizacoes: Dependabot acompanha `pip` e `github-actions`.
6. Dados de teste: somente dominios reservados, IDs sinteticos e marcadores redigidos.

## Controles da plataforma GitHub

Secret scanning, push protection, alertas de vulnerabilidade e correcoes automaticas devem ser habilitados quando suportados pelo repositorio. Esses controles complementam os testes; nao substituem a remocao preventiva de segredos.

## Separacao do backend

Nenhum controle local impede abuso do endpoint de login ou substitui autorizacao do servidor. Rate limiting, politicas de sessao e testes de abuso pertencem ao ActaskBack e permanecem explicitamente adiados.

