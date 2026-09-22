# Atritos com o `_shared` (pov-shared 0.1.4) — consumidor nº 3

## Instalação

`pip install -e "../_shared[tracing]"` no venv do PoV (Python 3.12.12): limpo, `pip check` sem
quebras, nenhuma versão existente alterada.

Os outros dois extras **não** entram neste venv — verificado com `pip install --dry-run`:

| Extra | Por que ficou de fora |
|---|---|
| `eval` | arrasta `anthropic 1.7.0` (o PoV está em `0.117.0`), `numpy 2.5.3`, `pandas`, `langchain*`, `langgraph`, `openai` — ~70 pacotes e uma troca de major do SDK que o `app/llm.py` usa direto |
| `guardrails` | arrasta `spacy`/`presidio`/`numpy 2.4.6` (~30 pacotes) só para o Presidio, que este PoV não precisa: o `mask_pii` por regex do núcleo já cobre o uso de borda |

Recomendação registrada: quem precisar de Ragas aqui cria `.venv-eval` separado
(`python3.12 -m venv .venv-eval && .venv-eval/bin/pip install -e "../_shared[eval]"`) em vez de
forçar downgrade no venv do PoV. O eval desta rodada (`backend/eval_routing.py`) é próprio e não
usa Ragas, então `EVAL_JUDGE_MAX_TOKENS` não aparece nos relatórios daqui.

## Atritos encontrados

1. **`tracing` lê só o ambiente do processo.** Com `TRACE_SINK=atlas`, `init_tracing` falha com
   `TRACE_SINK=atlas requer TRACE_MONGODB_URI ou MONGODB_URI` mesmo com a URI no `.env` do PoV,
   porque quem carrega esse `.env` é o `pydantic-settings`, não o `os.environ`. Contornado em
   `app/observability.py` (exporta `TRACE_MONGODB_URI` a partir de `get_settings()` antes de
   chamar `init_tracing`). Sugestão para o _shared: aceitar uma URI por parâmetro em
   `init_tracing(service_name, mongodb_uri=None)`.
2. **Falha de tracing é silenciosa para quem não configurou logging.** `init_tracing` loga um
   warning e devolve `off`; num script sem `logging.basicConfig` o retorno `off` aparece sem
   motivo. Sugestão: devolver o motivo junto (`("off", "TRACE_MONGODB_URI ausente")`) ou expor
   `last_error()`.
3. **Colisão de nomes com o PoV.** `guardrails` (topo, do _shared) x `app/guardrails.py` (deste
   PoV) convivem porque o do PoV é sempre importado como `app.guardrails`; mesma coisa para
   `tracing` x `app/observability.py`. Vale registrar como convenção: **nenhum módulo do PoV na
   raiz do `sys.path` pode se chamar `tracing`, `guardrails`, `grove_client` ou `evalkit`.**
4. **`grove_client.create_message` não se aplica aqui.** Este PoV fala com o SDK Anthropic
   direto (sem LangChain/LangGraph) e já tem retry com backoff, fallback de modelo e circuit
   breaker por endpoint em `app/llm.py`, incluindo contabilidade de tokens/custo por tentativa.
   Trocar por `create_message` perderia a contabilidade; a resiliência nova desta rodada foi na
   metade que faltava (tools) e no supervisor. Se o `_shared` quiser ser adotado aqui, o que
   ajudaria é o breaker/retry expostos como **decorador genérico**, independente de quem faz a
   chamada HTTP.
5. **`validate_output` com `max_repairs=0`** funciona como documentado (reparo por LLM é opt-in
   explícito) — sem atrito; ficou registrado porque é o default que este PoV usa de propósito no
   caminho de erro, onde uma chamada extra ao provedor é exatamente o que não se quer.
