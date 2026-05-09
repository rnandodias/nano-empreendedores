# Dicionário de Dados — Projeto Nano-empreendedores

Vocabulário interno do projeto. Atualizado pelo agente `data-engineer` ao final da Etapa 1.

## Convenções

- Nomes em **snake_case**, sem acentos.
- Tipos: `categoria`, `int`, `float`, `bool`, `data`, `string`.
- Toda variável aqui deve ter origem rastreável em pelo menos uma fonte (PNADC, Censo, MEI).
- Codificações categóricas usam strings semânticas (`"conta_propria"`), não códigos numéricos das fontes.

## Variáveis harmonizadas

| Nome interno | Tipo | Origem PNADC | Origem Censo | Origem MEI | Descrição | Observações |
|--------------|------|--------------|--------------|------------|-----------|-------------|
| `uf`         | categoria | UF | V0001 | UF | Sigla da UF (AC, AL, ..., TO, DF) | 27 valores |
| `municipio_ibge` | int | (não disponível) | V0002 | MUNICIPIO | Código IBGE do município | 7 dígitos |
| `sexo` | categoria | V2007 | V0601 | — | "masculino" \| "feminino" | |
| `idade_anos` | int | V2009 | V6036 | — | Idade em anos completos | |
| `cor_raca` | categoria | V2010 | V0606 | — | "branca" \| "preta" \| "parda" \| "amarela" \| "indigena" \| "ignorada" | |
| `escolaridade` | categoria | VD3004 | V6400 | — | "sem_instrucao" \| "fundamental" \| "medio" \| "superior" | Categorias colapsadas |
| `posicao_ocupacao` | categoria | VD4009 | V6920+ | — | "conta_propria" \| "empregado" \| "empregador" \| "domestico" \| "outro" | |
| `renda_mensal_brl` | float | VD4019 | V6531 | — | Rendimento mensal habitual de todos os trabalhos, em R$ correntes | Deflação opcional |
| `renda_anual_brl` | float | derivada | derivada | — | `renda_mensal_brl × 12` | |
| `cnae_secao` | categoria | V4010 → seção | V6471 → seção | CNAE_FISCAL → seção | Seção CNAE 2.0 (A-U) | Harmonizada |
| `cnae_classe` | string | V4010 | V6471 | CNAE_FISCAL | CNAE 5 dígitos | |
| `peso_amostral` | float | V1028 | peso_pessoa | (n/a) | Peso para expansão | Não usar em MEI |
| `upa` | int | UPA | (n/a) | (n/a) | Unidade primária de amostragem (PNADC) | |
| `estrato` | int | Estrato | (n/a) | (n/a) | Estrato amostral (PNADC) | |
| `is_nano_empreendedor` | bool | derivada | derivada | (n/a) | Atende à definição operacional | |
| `mei_ativo` | bool | (n/a) | (n/a) | SITUACAO_CADASTRAL | MEI ativo na data de referência | |

## Tabelas de codificação

### `cor_raca`
| Código PNADC | Código Censo | Valor harmonizado |
|---|---|---|
| 1 | 1 | branca |
| 2 | 2 | preta |
| 3 | 4 | amarela |
| 4 | 3 | parda |
| 5 | 5 | indigena |
| 9 | 9 | ignorada |

(Outras tabelas a serem preenchidas pelo `data-engineer` durante a Etapa 1.)
