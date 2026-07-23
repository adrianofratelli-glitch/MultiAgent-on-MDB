import { useEffect, useState } from 'react';
import { api } from '../api.js';

function short(text, max = 140) {
  if (!text) return '';
  const value = String(text);
  return value.length > max ? `${value.slice(0, max)}…` : value;
}

// Destaques de governança: o mesmo turno que respondeu ao cliente também prova,
// documento por documento, que a busca por contexto aconteceu ANTES do LLM
// (cascata: cache/curto prazo -> longo prazo -> fatos do cliente) e que tudo
// ficou isolado por customer_key (multi-tenant nativo, não filtro de app).
export function AiBrainHighlights({ customer, lastRun, timeline }) {
  if (!lastRun) return null;

  const cacheHit = lastRun.cache_hit;
  const cacheClass = cacheHit ? 'hit' : 'miss';
  const cacheTitle = cacheHit ? '⚡ Cascata semântica · HIT' : '🔄 Cascata semântica · MISS';
  const cacheDetail = cacheHit
    ? `Servido do MongoDB sem chamar o LLM · fonte: ${lastRun.cache_source === 'curto_prazo' ? 'short_term_memory (sessão atual)' : 'semantic_cache'} · ~${lastRun.tokens_economizados ?? 0} tokens economizados`
    : `Nenhuma correspondência em short_term_memory nem semantic_cache · turno seguiu para memória de longo prazo + LLM · ${lastRun.usage?.total ?? 0} tokens gastos`;

  const longTermEvent = (timeline || []).find((event) => event.collection === 'long_term_memory');
  const factsEvent = (timeline || []).find((event) => event.collection === 'customer_memory');
  const memDetail = `Longo prazo: ${longTermEvent ? `${longTermEvent.result?.count ?? 0} item(ns) recuperado(s) de long_term_memory` : 'nenhum item recuperado'}. Fatos do cliente: ${factsEvent ? 'novo fato extraído e persistido em customer_memory (supersessão)' : 'sem fato novo neste turno'}.`;

  const guardEvent = (timeline || []).find((event) => event.category === 'guardrail');
  const guardBlocked = guardEvent?.result?.blocked;
  const guardClass = guardBlocked ? 'blocked' : 'ok';
  const guardTitle = guardBlocked ? '🛡️ Guardrail · BLOQUEADO' : '🛡️ Guardrail de entrada · aprovado';
  const guardDetail = guardBlocked
    ? 'Turno interrompido antes de tocar qualquer agente ou LLM.'
    : `score ${guardEvent?.result?.score ?? '—'} · guardrail_denylist, isolado por área (${customer?.area ?? '—'})`;

  return (
    <div className="ai-brain-highlights">
      <div className="feat-card identity">
        <div className="feat-title">👥 Identidade & isolamento</div>
        <div className="feat-detail mono">{`${customer?.name ?? '—'} (customer_key: ${customer?.customer_key ?? '—'}) · área ${customer?.area ?? '—'} · toda query filtrada pelo customer_key do JWT, nunca pelo payload`}</div>
      </div>
      <div className={`feat-card cache-${cacheClass}`}>
        <div className="feat-title">{cacheTitle}</div>
        <div className="feat-detail mono">{cacheDetail}</div>
      </div>
      <div className={`feat-card guard-${guardClass}`}>
        <div className="feat-title">{guardTitle}</div>
        <div className="feat-detail mono">{guardDetail}</div>
      </div>
      <div className="feat-card mem">
        <div className="feat-title">🧠 Memória · curto + longo prazo</div>
        <div className="feat-detail mono">{memDetail}</div>
      </div>
    </div>
  );
}

const INSP_TABS = [
  { key: 'cache', label: 'semantic_cache' },
  { key: 'short', label: 'short_term_memory' },
  { key: 'long', label: 'long_term_memory' },
  { key: 'facts', label: 'customer_memory' },
];

// Inspetor "ai_brain": lê as mesmas 4 collections que a cascata consulta antes
// do LLM, sempre filtrado pelo customer_key da identidade logada — a prova
// visual de que governança/isolamento não é promessa, é o dado.
export default function AiBrainInspector({ customerKey, run }) {
  const [tab, setTab] = useState('cache');
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  const load = async () => {
    if (!customerKey) return; // login ainda não resolveu — evita 401 antes do token existir
    setLoading(true);
    setErr(null);
    try {
      setPayload(await api.inspector(tab));
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [tab, run, customerKey]);

  const items = payload?.items ?? [];

  return (
    <div className="ai-brain-inspector">
      <div className="ai-brain-inspector-head">
        <span className="collections-panel-label">ai_brain · collections consultadas antes do LLM</span>
        <div className="inspector-tabs-row">
          {INSP_TABS.map((t) => (
            <button key={t.key} className={`insp-tab ${tab === t.key ? 'active' : ''}`} onClick={() => setTab(t.key)}>{t.label}</button>
          ))}
          <button className="insp-mini" onClick={load} disabled={loading}>↻</button>
        </div>
      </div>
      {err && <div className="dim" style={{ padding: 8 }}>⚠ {err}</div>}
      {loading && <div className="dim" style={{ padding: 8 }}>carregando…</div>}
      {!loading && !err && (
        <div className="insp-body">
          <div className="dim mono insp-head">customer_key: {payload?.customer_key ?? customerKey} · {items.length} documento(s) mais recentes</div>
          {items.length === 0 && <div className="dim">Nada nesta collection ainda para esta identidade — pergunte algo e depois volte aqui.</div>}
          {items.map((item, index) => (
            <div key={item._id || index} className="insp-row">
              {(item.question_text || item.question) && <div className="insp-q mono">Q: {short(item.question_text || item.question, 160)}</div>}
              {item.answer && <div className="insp-a">A: {short(item.answer, 160)}</div>}
              {item.fact_type && <div className="insp-q">🔖 {item.value} <span className="dim">({item.fact_type})</span></div>}
              {!item.question_text && !item.question && !item.fact_type && item.text && <div className="insp-q">{short(item.text, 160)}</div>}
              <div className="insp-meta mono dim">
                {item.agent ? `agente: ${item.agent} · ` : ''}
                {item.scope ? `scope: ${item.scope} · ` : ''}
                {item.expires_at ? `expira ${short(item.expires_at, 19)} (TTL)` : ''}
                {item.active === false ? 'substituído (supersessão) · trilha de auditoria' : ''}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
