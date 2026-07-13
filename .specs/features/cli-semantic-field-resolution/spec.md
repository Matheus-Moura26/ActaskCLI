# Futuro: Resolução Semântica de Campos na CLI e Skill

**Status:** Planejado, não implementado  
**Prioridade:** Futuro próximo

## Problema

A CLI expõe contratos corretos para máquinas, como `assignee_id`, `column_id` e IDs de campos customizados. Uma IA, porém, recebe pedidos humanos como:

```text
Quais tasks tem para o João Gabriel?
```

Ela não pode adivinhar se `João Gabriel` é responsável, criador, opção de um campo customizado, cliente ou texto livre. Também não deve comparar nomes localmente contra uma página parcial de tasks.

## Objetivo

Permitir que a CLI e a skill descubram o esquema real de um projeto e resolvam nomes humanos para identificadores persistidos antes de consultar ou alterar tasks.

## Fluxo Esperado

Para “Quais tasks tem para o João Gabriel?” a skill deve:

1. Descobrir o projeto ou pedir qual projeto quando necessário.
2. Consultar membros/usuários autorizados do projeto e resolver `João Gabriel` como pessoa.
3. Quando houver um único resultado, consultar tasks com `assignee_id=<id>` e paginação completa.
4. Quando houver vários nomes semelhantes, apresentar as opções e pedir desambiguação.
5. Quando não houver pessoa correspondente, verificar somente campos configurados no projeto que possam aceitar esse valor.
6. Se o valor puder corresponder a mais de um campo, perguntar qual campo a pessoa quer usar; nunca assumir.
7. Informar o campo interpretado na resposta: por exemplo, “responsável: João Gabriel”.

## Capacidades Necessárias

### Descoberta de esquema

- Listar campos nativos pesquisáveis, seus nomes humanos e seus identificadores técnicos.
- Listar campos customizados ativos, tipo, opções e IDs.
- Informar se um campo aceita usuário, texto, número, data ou opções enumeradas.
- Listar membros do projeto com `id`, nome e e-mail mascarado quando apropriado.

### Resolução de valores

- Pessoa: nome parcial normalizado, com resultado único ou lista de candidatos.
- Opção customizada: label humano para valor persistido da opção.
- Coluna: nome humano para `column_id`.
- Campo: label/key humano para `field_definition_id` ou campo nativo.
- Texto/número/data: preservar o valor humano e usar o operador compatível com o tipo.

### Consulta segura

- CLI deve aceitar filtros semânticos documentados ou expor um comando de resolução que devolva IDs.
- A skill usa a resolução antes de `tasks list`; ela nunca envia “João Gabriel” a `assignee_id`.
- Contagens usam `meta.total` e listas paginam até completar o total.
- Resultados vazios devem dizer qual campo e valor foram pesquisados.

## Contratos Propostos

Alternativa preferida: a CLI oferece descoberta e resolução explícitas, mantendo `tasks list` simples.

```text
actask projects members <project-id> --search "João Gabriel" --json
actask projects fields <project-id> --json
actask projects resolve <project-id> --value "João Gabriel" --json
```

`resolve` retorna candidatos tipados, por exemplo:

```json
{
  "data": [
    { "kind": "user", "field": "assignee_id", "id": "user-uuid", "label": "João Gabriel" },
    { "kind": "custom_option", "field_definition_id": "field-uuid", "value": "joao-gabriel", "label": "João Gabriel" }
  ]
}
```

A skill só escolhe automaticamente quando existe um único candidato compatível com o pedido explícito. Caso contrário, pergunta qual interpretação usar.

## Alterações Futuras na Skill

- Adicionar “Schema and Value Resolution Guard” antes de filtros por pessoas ou valores humanos.
- Tratar sufixos técnicos (`_id`, `_ids`, `field_definition_id`) como contrato de transporte, não como linguagem para o usuário.
- Explicar respostas usando labels humanos e incluir o campo interpretado.
- Proibir inferir que todo nome é `assignee_id` ou que toda opção pertence ao campo Status.

## Critérios de Aceite

- [ ] “Tasks para João Gabriel” resolve um único membro como `assignee_id` e retorna todas as tasks paginadas.
- [ ] Dois membros com nomes semelhantes geram pergunta de desambiguação.
- [ ] Um valor que existe em dois campos customizados gera pergunta de campo.
- [ ] Campo customizado enum usa valor persistido após resolver seu label.
- [ ] A resposta informa a interpretação usada e nunca expõe IDs sem necessidade humana.
- [ ] Falha de resolução não gera filtro amplo nem resultado inventado.
