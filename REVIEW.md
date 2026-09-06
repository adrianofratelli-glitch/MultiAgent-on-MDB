> Estado vigente: melhoria `5cd4bd9` aprovada pelo usuário e integrada em `main`. As menções abaixo a aprovação pendente são históricas. As propostas de core/schema/dataset continuam sem aplicação.

# Revisão de engenharia e design — multiagente-atendimento

## Resultado

Import de tipo DataStore corrigido no teste de grafo, eliminando F821.

Branch `review/codex-improvements`, criada de `main` em `da4e598d21dd7bf8a840e63d1f952ecc73f31712`. Sem merge, push, troca de biblioteca core, alteração de schema ou dataset.

## Commits de correção

- `986aab2 fix: resolve DataStore annotation in graph regression tests`

## Commits visible-change

Nenhum.

## Validação

- 70 testes unitários passaram em DEMO_MODE.
- Build de produção passou; análise Ruff E9/F63/F7/F82 com target Python 3.12 passou.
- Browser com APIs bloqueadas: 1440×1000, 768×1024 e 360×800; sem pageerror e sem overflow horizontal no shell inicial; link de salto transfere foco ao conteúdo.
- As 14 cópias de pov-signature.css permanecem idênticas; lang pt-BR confirmado. Nenhuma alteração na camada compartilhada de CSS.
- Auditor de portas passou: registro e configurações alinhados.
- npm audit do lockfile após correções: 0 altos, 0 críticos, 0 moderados e 0 baixos.

## Sugestões não aplicadas e limites

- DEMO_MODE valida contratos locais, não qualidade de busca vetorial nem retomada real do Change Stream.
- Preservados escopo customer_key, guardrails e oito agentes reais. Não alterados thresholds, políticas persistidas ou modelos.

A verificação visual cobre o shell offline e abas acessíveis sem backend, não todos os estados de dados. Não certifica contraste de cada componente, comportamento touch completo ou toda a navegação com Atlas. Fluxos reais de escrita/carga não foram executados para preservar datasets. Nenhuma comparação de performance foi inventada. Evidências locais: `/tmp/codex-portfolio-review/`.

## Dependências Python

Auditoria do ambiente instalado, não de uma resolução limpa do manifesto; ferramentas de desenvolvimento podem aparecer junto com runtime. Os IDs abaixo não equivalem a exploração confirmada na PoV. Reconciliar versões instaladas/manifests e testar compatibilidade; atualizações core/major ficaram fora desta rodada. Pacotes de ferramenta e componentes extras do venv também não foram alterados fora da branch.

| Pacote instalado | Versão | Advisory | Versões corrigidas informadas |
|---|---|---|---|
| pip | 26.0 | PYSEC-2026-196, PYSEC-2026-2875, PYSEC-2026-2876, PYSEC-2026-3721 | 26.1, 26.1.2, 26.2 |
| pytest | 8.4.2 | PYSEC-2026-1845 | 9.0.3 |

## Segredos e compartilhamento

Varredura por padrões de chaves privadas, chaves Anthropic/AWS e URI MongoDB autenticada no histórico Git local alcançável: nenhuma credencial real confirmada; matches encontrados eram placeholders conhecidos. Limite: não é scanner de entropia, não cobre objetos inacessíveis, texto em screenshots nem logs externos.

Nenhum import/referência estática a `_shared/grove_client.py` foi encontrado nesta PoV. Configuração própria de gateway/ambiente não constitui dependência de código desse módulo. `_shared` permaneceu intocado; consumidores externos/dinâmicos não são garantidos por busca estática. Relatório separado: `../REVIEW_SHARED.md`.


## Fechamento final — 2026-09-05

Esta seção atualiza o estado dos achados históricos acima.

- Aplicado/reavaliado: Sem alteração nova de runtime; guardrails e oito agentes preservados.
- Validação: 70 testes em DEMO_MODE; npm sem achados.
- Propostas e limites restantes: pytest 8.4.2 → 9.0.3: corrige advisory local, mas salto major requer compatibilidade de plugins/CI. Busca vetorial e retomada Change Stream reais exigem integração; DEMO_MODE não os certifica. Sem alteração de customer_key, thresholds, modelos ou políticas persistidas.
- pip-audit atual: pytest 8.4.2: PYSEC-2026-1845
- Ambiente: pip 26.2.1 nos ambientes que possuem pip; FinScope mantém uv sem pip. Essa atualização local não altera arquivos de dependências das PoVs.
- `_shared`: nenhum importador estático comprovado nesta PoV; apenas smoke consome o helper no inventário.


## Homologação de resiliência e UI

- Melhoria: Impedir chat concorrente com troca de identidade, limpar contexto anterior e bloquear cliques duplicados; limitar JSON a 30 s/chat a 300 s; liberar leitor SSE e aceitar CRLF.
- Isolamento: `review/codex-homologation`, baseada no HEAD `1f05a38`. Mudança de estado observável; aguardando aprovação individual, sem merge.
- Validação: build passou; UI offline em 1440×1000, 768×1024 e 360×800 sem pageerror nem overflow horizontal; skip link transfere foco. 2 testes novos de transporte/polling neste repositório. As suítes locais anteriores foram reexecutadas; resultados consolidados no vault PoVs-Handoffs.
- Limite: teste offline/fixture não certifica cenário real completo nem ausência de bugs. Não houve alteração de schema, dataset ou dependência core.
- Propostas preservadas: pytest 8.4.2 → 9.0.3: corrige advisory local, mas salto major requer compatibilidade de plugins/CI. Busca vetorial e retomada Change Stream reais exigem integração; DEMO_MODE não os certifica. Sem alteração de customer_key, thresholds, modelos ou políticas persistidas.
- `_shared` e daemon do portal não foram alterados nesta rodada.
