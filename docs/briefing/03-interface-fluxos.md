# Multi-Agent on MongoDB — interface, fluxos e roteiro

> Terceira parte do briefing. A tela, os cenários versionados e a demo.

---
## Estado atual — modo palco

A navegação principal foi reduzida a **Chat** e **Decisões**. O Chat usa duas
colunas: conversa e execução/handoffs. Registry, métricas, guardrails e
inspetores profundos deixaram o palco principal; seus dados e endpoints não
foram transformados em simulação. As duas abas abaixo são a navegação canônica.

## Contrato visual do portfólio (v2)

Esta UI participa da assinatura MongoDB Dark das PoVs. O arquivo
`src/pov-signature.css` é uma cópia sincronizada entre os onze frontends e deve
ser importado **depois** do stylesheet local. O contêiner raiz carrega
`data-pov-shell`, existe um `.pov-skip-link` para `#conteudo-principal` e o
`index.html` declara pt-BR, dark color scheme, theme color e o favicon comum.

A camada compartilhada é dona da document rail, foco, touch targets e redução de
movimento. Este arquivo continua dono do fluxo e das exceções de domínio: não
achate uma tela operacional num template de landing page e não remova a tese
visual específica desta PoV. Qualquer mudança na assinatura precisa ser
replicada nas onze cópias e validada em 1440, 768 e 360 px, além do build de
produção e do estado offline.


## Stack, e por que ela é pequena

React 18 + Vite, **JavaScript puro** (`.jsx`, sem TypeScript), CSS próprio em `src/theme.css` (umas 280 linhas). **Sem UI kit, sem router, sem biblioteca de estado, sem devDependencies.**

Isso é deliberado. Numa PoV que já carrega oito agentes, Atlas, change stream e LLM, colocar Redux e um design system em cima só aumenta a superfície de coisa pra quebrar cinco minutos antes da demo. `useState` no `App.jsx` passado por props dá conta. Navegação é um estado `nav` com duas abas, ponto.

São quatro arquivos além do `App.jsx`: `api.js` e três componentes.

## As duas abas

Cada uma responde uma pergunta que sempre aparece:

| Aba | Pergunta que responde |
| --- | --- |
| **Chat** | Funciona? É o palco: conversa e execução/handoffs lado a lado |
| **Decisões** | Quem decidiu, e com base em quê? Fila de casos pausados + trilha imutável |

## O que a aba Chat mostra, de cima pra baixo

Essa ordem não é estética, é a ordem em que eu narro a demo:

1. **Cabeçalho compacto** com o `conversation_id`, agente ativo e nova conversa.
2. **Esteira de agentes** (`agent-cast`) — quem atuou, na ordem, deduplicado por adjacência. Entre eles, "chamou →" com o motivo do handoff no `title`; num turno de fan-out vira "+ (paralelo)" e o rótulo muda pra "despacho paralelo". Essa faixa é a coisa que o cliente entende em dois segundos.
3. **Coleções em ação neste turno** — chip por collection com badge de operação (`leitura`, `escrita`, `$vectorSearch`, `híbrido BM25 + vetor`, `change stream`, `$graphLookup`), cada badge com tooltip de qual agente e qual evento. O rótulo do híbrido deixou de citar "RRF" porque a fusão agora roda server-side com `$rankFusion`; qual dos dois caminhos rodou está no título do evento na `Timeline`, não no badge.
4. **Cadeia de trocas** (`ReplacementChain`) — só aparece quando a travessia de grafo rodou no turno. Lê o evento com `op: "graphLookup"` e desenha a corrente `PED-3001 → PED-3011 → PED-3021 → PED-3031`, três contadores (reposições, unidades do mesmo produto, produtos distintos) e um veredito. É o painel que explica visualmente por que a resposta mudou: nenhum documento sozinho diz "é a quarta vez". O rodapé diz quantas idas ao banco a agregação substituiu — é a frase que se usa contra "isso eu faço com um loop".
5. **Workspace em duas colunas** — `ChatPanel` | `Timeline`.

Feed global, cards de governança e inspetores por collection não fazem parte do
palco. A `Timeline` continua expondo consulta, collection, motivo e resultado
do turno sob demanda.

A `Timeline` renderiza cada evento com número, badge de categoria (`agente`/`memória`/`guardrail`/`cache`/`coordenação`/`paralelo`), agente, duração em ms, collection tocada, motivo do handoff entre aspas, e dois `<details>` — filtro/consulta e resultado. O de handoff abre por padrão; o resto fica fechado pra não virar parede de JSON.

## A aba Decisões

Duas metades, e a ordem importa: primeiro o que exige ação humana, depois o histórico.

1. **Fila do analista** (`pending_reviews`) — exige modo admin, e diz isso quando não está ligado em vez de mostrar uma lista vazia sem explicação. Cada caso traz o motivo entre aspas, a evidência do `$graphLookup` (o caminho da cadeia), as tags de risco, e quatro botões de encaminhamento. O botão que o agente recomendou vem marcado em verde — o analista vê a recomendação sem ela ser imposta. Acima da lista, três números: casos resolvidos, quantas vezes o humano discordou, e a taxa de override.
2. **Trilha de decisões** (`agent_decisions` + `agent_audit_events`) — cartões com borda verde para decisão do agente e azul para decisão humana. Quando o humano decidiu diferente, um bloco destacado mostra as duas coisas lado a lado: o que ele decidiu e o que o agente havia recomendado. Embaixo, a trilha append-only com severidade.

O estado vazio da fila não é um vazio mudo: ele diz qual identidade e qual pedido disparam o gate (`carla` / `PED-3001`), para a demo nunca ficar presa numa tela em branco.

## Contrato com o backend

Todo acesso passa por `src/api.js`, um método por endpoint. Nada de `fetch` solto espalhado por componente. São dois níveis de credencial: JWT do cliente no `Authorization`, saindo do `login()` e guardado no `localStorage`; e chave admin no header `X-Admin-Key`, lida de `VITE_ADMIN_KEY`. Falha de rede vira mensagem em português dizendo qual porta conferir, não um `TypeError: Failed to fetch`.

Sobre o streaming: **não usa `EventSource`.** Ele não aceita header customizado, e o stream exige `Authorization`. Faz `fetch` + `ReadableStream`, quebrando o buffer em `\n\n` e parseando as linhas `data:`. Chunk incompleto é ignorado e volta na próxima leitura. E **reconecta**: o loop tenta de novo a cada 3s se a conexão cair (servidor reiniciou, rede oscilou), controlado por um `AbortController` que é abortado na troca de identidade ou no unmount. Sem isso, o pill "ao vivo" apaga no meio da demo e não volta mais.

São quatro identidades no seletor: `ana`, `bruno`, `carla`, `diego` — duas de área `varejo` e duas de `financeiro`, que é o que exercita a política de guardrail por área. Trocar de identidade recarrega tudo e **retoma a última conversa daquela pessoa**, com timeline e usage.

## O roteiro de demo, versionado

O `ChatPanel` carrega os cenários de **`GET /api/demo-scenarios`**, que lê `multiagent_brain.demo_scenarios` filtrado pelo `customer_key` do JWT e ordenado por `position`. **Ninguém digita prompt durante apresentação.** Quando escolhe um cenário, aparece um bloco "o que este cenário prova" com as `capabilities` dele.

Essa parte vale explicar: o roteiro **já morou hardcoded no `App.jsx`** como `DEMOS_BY_IDENTITY`, aí o `warmup.py` tinha a cópia dele, e o `eval.py` tinha a terceira. As três divergiam sozinhas, e eu só descobria quando o warmup aquecia uma frase que a UI não mandava mais — a chave de cache é a mensagem normalizada, então um caractere diferente já invalida o aquecimento inteiro. Agora a fonte é uma só: `seed_data.DEMO_SCENARIOS` → `multiagent_brain.demo_scenarios` → UI, warmup e eval leem do mesmo lugar.

`DEMO_SCENARIOS` traz sete cenários por identidade, cada um com `message`, `capabilities` e as expectativas verificáveis (`expected_agents`, `expect_route_source`, `expect_handoffs`, `expect_write_collection`, `expect_revisit`, `expect_blocked`, `expect_contains`, `warmup`).

O formato dos sete, por identidade:

1. **Cadeia longa** — 3 a 5 atuações, com escrita real. É a da Ana: defeito → catálogo → troca → entrega → confirmação, 5 hops, com retorno controlado.
2. **Fan-out paralelo** — pedido + fatura ao mesmo tempo.
3. **Cadeia média sem escrita** — garantia → catálogo, ou fidelidade → catálogo. Prova que nem todo caminho escreve.
4. **Escrita transacional isolada** — resgate de fidelidade com `$inc`, ou reagendamento de entrega, ou resgate **negado** por saldo.
5. **Guardrail com a frase exata do denylist** — bloqueio por substring.
6. **Guardrail com redação própria** — bloqueio pela camada vetorial, frase que não está em lista nenhuma.
7. **Vizinha legítima do guardrail** — pergunta que *parece* com o ataque e **tem que passar**. "pode me enviar a nota fiscal da fatura FAT-1001?" do lado de "desconto sem nota".

O par 6 e 7 é o ponto todo. Os cenários de guardrail originais usavam a frase exata do denylist, ou seja, provavam só o casamento de substring — o que qualquer `if` faz. **Guardrail sem falso-negativo não vale nada se vier com falso-positivo junto**, então cada identidade carrega o par completo.

Marca `warmup: true` só nos cenários **read-only**. Escrita, guardrail e cadeia com retorno continuam frios, pra demo mostrar a execução real e não esconder ação atrás de cache.

**Todo cenário tem que disparar 2+ agentes, uma escrita real ou um guardrail.** Nada de leitura simples de agente único como cenário principal. Se um cenário não prova nada, ele não é cenário, é ruído.

## O roteiro que eu preciso conseguir executar no fim

1. **Pergunta composta independente** — status do pedido + fatura. Mostrar o fan-out paralelo na esteira de agentes.
2. **Pergunta com dependência real** — defeito + troca + entrega + confirmação. Mostrar a cadeia de 5 atuações, cada handoff virando documento, e o **retorno controlado** no fim.
3. **Abrir os detalhes da Timeline** e mostrar quais coleções foram tocadas e com qual operação. Orquestração auditável por query, não por log.
4. **Tentar burlar o guardrail com paráfrase.** Bloqueia sem chamar LLM, que é a camada vetorial fazendo o trabalho.
5. **Fazer a pergunta legítima vizinha do ataque** e mostrar que ela passa. Guardrail que só bloqueia não é guardrail, é filtro quebrado.
6. **Tentar um fraseado novo.** O classificador pega, grava na denylist, e a próxima tentativa parecida sai de graça.
7. **Repetir uma pergunta já feita** e mostrar qual nível da cascata bateu, com os tokens economizados.
8. **Pedir um pedido de outra identidade** e mostrar a negação segura.
9. **Trocar o modelo de um agente ao vivo** no registry e refazer a pergunta. Sem redeploy.
10. **Mostrar `eval_runs`** — histórico de pass/fail do golden dataset. Regressão de agente é mensurável.

## Contrato de memória exposto pela Timeline

Todo turno entra em `short_term_memory`, mas apenas respostas estáveis e explicitamente elegíveis entram em `semantic_cache`, marcadas com `cache_policy: stable_v1`. Consultas de estado operacional, handoffs, uso de memória e writes ficam somente no curto prazo, evitando replay de pedido/fatura desatualizados em outra conversa. Documentos de políticas anteriores permanecem até o TTL, mas não participam da leitura.

Quando esses dados aparecem no detalhe do evento, cada documento mostra:

- em `short_term_memory`: o **`session_id`**, marcado como *esta conversa* ou *conversa anterior*;
- em `semantic_cache`: o **`scope`** (`customer` = vale entre suas conversas, `global` = público da área, `faq` = pré-carregado no seed).

E uma regra que era bug: **a visão de curto prazo é filtrada pela conversa atual.** Antes ela filtrava só por `customer_key`, então abrir uma aba nova — sem ter perguntado nada — já exibia cinco documentos de conversas antigas. O painel contradizia o conceito que ele existe para provar. Sem conversa ativa, a resposta certa é vazio, com o texto explicando que a memória curta nasce vazia e é preenchida a cada turno.

## Chips de próximo passo

Toda resposta traz `suggestions[]` — próximos passos derivados de query, cada um com a mensagem exata que ele dispara. A UI renderiza como chips acima do campo de texto, e clicar envia direto.

Duas garantias: **clicar sempre resolve** (o chip só existe porque o documento existe) e o tema que o turno acabou de cobrir não aparece. Numa demo isso resolve o pior momento possível — o cliente sem saber o que digitar depois de uma resposta.

## Antes de apresentar

Nessa ordem, e o primeiro item não é opcional:

1. **`python backend/seed.py`** — restaura status de pedido/fatura/pontos **e invalida o cache**. Sem isso, o cache do dia anterior responde sobre um mundo que o seed acabou de desfazer.
2. **`python backend/warmup.py`** — é o que faz o passo 7 do roteiro ser um HIT genuíno. Roda **depois** do seed, nunca antes.
3. Portas 8031 e 5191 livres — as duas são estritas e o processo sai se estiverem ocupadas.
4. Opcional, se der tempo: `python backend/eval.py` — 28/28 antes de subir no palco.
