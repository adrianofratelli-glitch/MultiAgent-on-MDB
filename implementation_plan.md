# Multi-Agent on MongoDB — prompt de construção

> Esse é o briefing que eu entrego **antes de existir uma linha de código**. Não é documentação do que existe: é o que eu daria pra alguém (ou pro Claude) subir a PoV inteira do zero.

Atendimento ao cliente com **oito agentes coordenados**, onde o MongoDB Atlas é ao mesmo tempo o data plane e o coordination plane: regra de roteamento, estado, handoff, memória, cache, guardrail, roteiro de demo e histórico de avaliação são todos documento. Backend FastAPI em `:8031`, frontend React/Vite em `:5191`, bases `multi_agent_poc` + `multiagent_brain`.

A tese: **não precisa de fila, workflow engine e vector DB separados pra orquestrar agente.** E o efeito colateral, que é o melhor argumento: toda decisão da orquestração fica inspecionável por query.

| Arquivo | O que responde |
|---|---|
| [`docs/briefing/01-arquitetura.md`](docs/briefing/01-arquitetura.md) | os oito agentes, roteamento determinístico-primeiro, cadeia/retorno controlado/fan-out, guardrail em três camadas, gateway LLM, segurança, escritas reais, `DEMO_MODE`, ordem de trabalho |
| [`docs/briefing/02-mongodb.md`](docs/briefing/02-mongodb.md) | as duas bases, a estratégia de embedding (autoEmbed voyage-4 1024d cosine `flat`), os 8 índices vetoriais + o lexical com seus campos `filter`, índices regulares/únicos/TTL, validadores `$jsonSchema`, e **todas as queries com o pipeline colado** — a cascata com `$unionWith`, guardrail semântico, ranking ponderado do catálogo, híbrido BM25+vetor com RRF, supersessão, escritas dos agentes e o Change Stream |
| [`docs/briefing/03-interface-fluxos.md`](docs/briefing/03-interface-fluxos.md) | as duas abas, a anatomia da aba Chat, contrato de API e streaming, os sete cenários por identidade, roteiro de demo |

Se for ler só um: o **01**, pela regra de roteamento. LLM sobrepondo decisão determinística torna a demo não-reprodutível.
