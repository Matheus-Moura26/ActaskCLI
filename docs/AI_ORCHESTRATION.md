# AI Orchestration Guide for Actask CLI v1

Este documento e o ponto de entrada para um orquestrador de IA implementar a v1.

## 1. Bootstrap

1. Ler `AGENTS.md` e `.specs/STATE.md`.
2. Ler integralmente `spec.md`, `design.md` e `tasks.md` da feature `cli-v1`.
3. Confirmar acesso local aos repositorios `ActaskCLI` e `ActaskBack`.
4. Confirmar branch limpa ou identificar alteracoes do usuario sem modifica-las.
5. Selecionar somente a proxima tarefa cujas dependencias estejam concluidas.

## 2. Per-task cycle

Para cada tarefa:

1. Reconfirmar os requisitos e criterios de aceite vinculados.
2. Inspecionar o codigo e os testes existentes antes de decidir a implementacao.
3. Registrar decisoes novas em `.specs/STATE.md`.
4. Implementar o menor conjunto coeso de mudancas.
5. Criar ou atualizar testes na mesma tarefa.
6. Executar o gate especifico e registrar comando, resultado e contagem.
7. Revisar o diff em busca de segredos, escopo indevido e regressao de autorizacao.
8. Criar um unico commit atomico com a mensagem indicada.
9. Atualizar o handoff e marcar a tarefa concluida somente com evidencia.

## 3. Cross-repository work

T01 pode apenas documentar gaps. T02 esta explicitamente autorizada a propor mudancas no backend, mas o orquestrador deve executar cada gap como uma unidade independente, com testes de autorizacao. Nunca simular seguranca filtrando respostas somente na CLI.

Quando uma mudanca de contrato for necessaria:

1. Especificar primeiro o comportamento no `ActaskCLI`.
2. Implementar e testar a autorizacao no `ActaskBack`.
3. Publicar ou fixar o contrato de API.
4. Implementar o cliente da CLI.
5. Executar testes de contrato contra ambos.

## 4. Worker allocation

O orquestrador pode delegar uma fase por vez a um worker. Nao delegar uma tarefa para varios workers nem executar fases dependentes em paralelo. Cada worker recebe apenas:

- spec, design e tarefas da v1;
- estado e decisoes atuais;
- fase atribuida;
- caminhos dos repositorios;
- gates e invariantes de seguranca.

O worker devolve commits, testes executados, contagem, desvios e riscos. O orquestrador valida o resultado antes da fase seguinte.

## 5. Skill implementation

Na T11, usar a Skill oficial de criacao de Skills:

1. Inicializar `actask-cli` em `skills/` com recursos `references`.
2. Escrever frontmatter apenas com `name` e `description`.
3. Colocar gatilhos completos na `description`.
4. Manter o corpo procedural, conciso e em forma imperativa.
5. Mover catalogo de comandos e schemas para `references/commands.md`.
6. Gerar `agents/openai.yaml` pela ferramenta oficial.
7. Executar o validador oficial e corrigir todos os erros.
8. Fazer forward tests com agentes sem acesso as conclusoes do autor.

## 6. Security stop conditions

Parar a fase e reportar ao usuario quando:

- uma rota permite acesso sem associacao ou permissao esperada;
- uma credencial aparece em logs, argumentos, fixtures ou diffs;
- o backend nao consegue distinguir `401` e `403`;
- um teste de autorizacao falha ou nao discrimina implementacao insegura;
- uma acao destrutiva pode ocorrer sem confirmacao explicita;
- a implementacao exige ampliar o escopo da v1 ou alterar uma decisao registrada.

## 7. Final verification

A autoria e a verificacao devem ser independentes. O verificador:

1. Le a especificacao sem receber a conclusao do implementador.
2. Mapeia cada requisito e criterio para evidencia executavel.
3. Executa suites e smoke tests em checkout limpo.
4. Testa autorizacao tambem por chamadas diretas a API.
5. Injeta falhas controladas para confirmar que os testes detectam bypass de projeto e permissao.
6. Inspeciona artefatos e historico em busca de segredos.
7. Produz `validation.md` com PASS ou FAIL e evidencias por criterio.

Somente um PASS integral autoriza a tag `v1.0.0`.
