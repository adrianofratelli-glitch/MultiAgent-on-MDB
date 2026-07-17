import { useEffect, useMemo, useState } from 'react';
import { api } from './api.js';
import Inspector from './components/Inspector.jsx';
import Timeline from './components/Timeline.jsx';

const NAV = ['Chat', 'Agentes', 'Guardrails', 'Métricas'];
const OP_LABELS = { read: 'leitura', write: 'escrita', vectorSearch: '$vectorSearch', hybridSearch: 'BM25 + vetor (RRF)', changeStream: 'change stream' };
const IDENTITIES = ['ana', 'bruno', 'carla', 'diego'];

function ChatPanel({ messages, input, setInput, send, busy, customerName, demos }) {
  const [selectedScenario, setSelectedScenario] = useState(null);
  return (
    <section className="chat-panel">
      <div className="panel-label">canal do cliente</div>
      <div className="messages">
        {messages.length === 0 && (
          <div className="welcome-message"><span>Olá, {customerName || 'cliente'}.</span><p>Em que posso ajudar com seu pedido, produto ou cobrança?</p></div>
        )}
        {messages.map((message, index) => (
          <div className={`message ${message.role}`} key={index}>
            <small>{message.role === 'user' ? 'você' : message.agent || 'assistente'}</small>
            {message.role === 'assistant' && (
              <span className={`cache-badge ${message.cacheHit ? 'hit' : 'miss'}`}>
                {message.cacheHit
                  ? `⚡ HIT (${message.cacheSource === 'curto_prazo' ? 'sessão atual' : 'cache global'}) — 0 tokens`
                  : `🔄 MISS — ${message.tokens ?? 0} tokens, contexto de longo prazo usado: ${message.longTermUsed ? 'sim' : 'não'}`}
              </span>
            )}
            <div>{message.text}</div>
          </div>
        ))}
      </div>
      <form className="chat-form" onSubmit={(event) => { event.preventDefault(); send(); }}>
        <textarea value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send(); } }} placeholder="Digite sua solicitação… (Enter envia, Shift+Enter quebra linha)" rows="3" />
        <button className="send-button" disabled={busy || !input.trim()}>{busy ? 'Coordenando…' : 'Enviar turno'}<span>↗</span></button>
      </form>
      <label className="demo-picker">
        <span>roteiro rápido</span>
        <select value="" onChange={(event) => {
          const demo = demos[Number(event.target.value)];
          if (demo) {
            setInput(demo.message);
            setSelectedScenario(demo);
          }
        }}>
          <option value="">Carregar um cenário de demonstração…</option>
          {demos.map((demo, index) => <option key={demo.scenario_id} value={index}>{demo.label}</option>)}
        </select>
        {selectedScenario && (
          <div className="scenario-proof">
            <span>o que este cenário prova</span>
            <div>{selectedScenario.capabilities.map((capability) => <code key={capability}>{capability}</code>)}</div>
          </div>
        )}
      </label>
    </section>
  );
}

function AgentsPage({ agents, adminMode, setAdminMode, reload }) {
  const toggle = async (agent) => {
    if (!adminMode) return;
    await api.updateAgent(agent.agent_key, { active: !agent.active });
    reload();
  };
  return (
    <section className="full-page-section">
      <div className="section-copy">
        <span className="eyebrow">ai_brain.agent_registry</span><h2>O time de agentes é uma collection.</h2>
        <p>Modelo, persona, ferramentas e budget mudam por documento — sem deploy. {agents.length} agentes reais, todos respondem de fato — nenhum documento de enfeite.</p>
        <label className="admin-toggle">
          <input type="checkbox" checked={adminMode} onChange={(event) => setAdminMode(event.target.checked)} />
          <span className="admin-toggle-track"><span className="admin-toggle-thumb" /></span>
          modo admin {adminMode ? '(ligado)' : '(desligado)'}
        </label>
      </div>
      <div className="agent-grid">{agents.map((agent) => (
        <article className={`agent-card ${agent.active ? '' : 'disabled'}`} key={agent.agent_key}>
          <div className="agent-card-head"><span className="agent-index">{agent.agent_key === 'orchestrator' ? 'Ø' : agent.agent_key.charAt(0).toUpperCase()}</span><button className="switch" disabled={!adminMode} aria-label={`Ativar ${agent.label}`} aria-pressed={agent.active} onClick={() => toggle(agent)}><span /></button></div>
          <h3>{agent.label}</h3><code>{agent.agent_key}</code><p>{agent.persona}</p>
          <dl><div><dt>modelo</dt><dd>{agent.model}</dd></div><div><dt>budget</dt><dd>{agent.max_turn_tokens} tok</dd></div><div><dt>tools</dt><dd>{agent.allowed_tools.join(', ')}</dd></div></dl>
        </article>
      ))}</div>
    </section>
  );
}

function DataPage({ title, subtitle, children }) {
  return <section className="full-page-section"><div className="section-copy"><span className="eyebrow">plano de coordenação</span><h2>{title}</h2><p>{subtitle}</p></div><div className="data-surface">{children}</div></section>;
}

function MetricsPage({ metrics, evalRuns, adminMode }) {
  const counters = metrics?.counters || {};
  const route = metrics?.routes?.chat || {};
  const cacheHits = Object.entries(counters).filter(([key]) => key.startsWith('cache.hits.')).reduce((sum, [, value]) => sum + value, 0);
  const cacheMisses = counters['cache.misses'] || 0;
  const cacheTotal = cacheHits + cacheMisses;
  const specialistAgents = Object.entries(counters)
    .filter(([key, value]) => /^agent\.(?!orchestrator)[^.]+\.turns$/.test(key) && value > 0)
    .length;
  const handoffCount = Object.entries(counters)
    .filter(([key]) => key.endsWith('.handoffs'))
    .reduce((sum, [, value]) => sum + value, 0);
  const businessCollections = new Set(['orders', 'support_tickets', 'redemptions', 'shipments']);
  const businessWrites = Object.entries(counters)
    .filter(([key]) => key.startsWith('collection.') && key.endsWith('.write') && businessCollections.has(key.slice('collection.'.length, -'.write'.length)))
    .reduce((sum, [, value]) => sum + value, 0);
  const nativeSearches = Object.entries(counters)
    .filter(([key]) => key.startsWith('collection.') && (key.endsWith('.vectorSearch') || key.endsWith('.hybridSearch')))
    .reduce((sum, [, value]) => sum + value, 0);
  const collectionRows = Object.entries(counters).reduce((rows, [key, value]) => {
    if (!key.startsWith('collection.')) return rows;
    const parts = key.slice('collection.'.length).split('.');
    const op = parts.pop();
    const collection = parts.join('.');
    const row = rows.get(collection) || { collection, read: 0, write: 0, vectorSearch: 0, hybridSearch: 0, changeStream: 0 };
    row[op] = value;
    rows.set(collection, row);
    return rows;
  }, new Map());
  const cards = [
    ['turnos concluídos', counters['route.chat.ok'] || 0, 'API /api/chat'],
    ['agentes exercitados', `${specialistAgents}/7`, 'especialistas com atuação real'],
    ['handoffs', handoffCount, `${counters['coordination.revisits'] || 0} retornos controlados`],
    ['escritas de negócio', businessWrites, 'orders · tickets · resgates · entregas'],
    ['buscas nativas', nativeSearches, 'Vector Search + híbrida RRF'],
    ['latência p95', route.p95_ms ? `${Math.round(route.p95_ms)} ms` : '—', `${route.count || 0} amostras`],
    ['cache hit rate', cacheTotal ? `${Math.round((cacheHits / cacheTotal) * 100)}%` : '—', `${cacheHits} hits · ${cacheMisses} misses`],
    ['guardrails', counters['guardrails.blocked'] || 0, 'turnos bloqueados'],
  ];

  return (
    <section className="full-page-section">
      <div className="section-copy">
        <span className="eyebrow">observabilidade operacional</span>
        <h2>O valor aparece no fluxo, não no log.</h2>
        <p>Cobertura, coordenação e operações MongoDB em uma leitura executiva. Tokens e latência continuam no payload técnico, mas não são tratados como números de sucesso.</p>
      </div>
      <div className="metric-grid">
        {cards.map(([label, value, note]) => <article className="metric-card" key={label}><span>{label}</span><strong>{value}</strong><small>{note}</small></article>)}
      </div>
      <div className="metric-ledger">
        <div className="panel-label"><span>coleções em operação</span><code>collection.*</code></div>
        {collectionRows.size === 0
          ? <p className="metric-empty">Execute um cenário no Chat para materializar leituras, escritas e buscas.</p>
          : <div className="metric-table-wrap"><table><thead><tr><th>collection</th><th>read</th><th>write</th><th>vector</th><th>hybrid</th></tr></thead><tbody>
            {[...collectionRows.values()].sort((a, b) => a.collection.localeCompare(b.collection)).map((row) => <tr key={row.collection}><td><code>{row.collection}</code></td><td>{row.read}</td><td className={row.write ? 'hot' : ''}>{row.write}</td><td>{row.vectorSearch}</td><td>{row.hybridSearch}</td></tr>)}
          </tbody></table></div>}
      </div>
      <div className="eval-panel">
        <div className="panel-label"><span>qualidade · GoalSuccessRate</span><code>eval_runs</code></div>
        {!adminMode && <p className="metric-empty">Ative o modo admin em Agentes para consultar o histórico de avaliação.</p>}
        {adminMode && !evalRuns.length && <p className="metric-empty">Nenhuma execução registrada. Rode <code>python eval.py</code> no backend.</p>}
        {adminMode && evalRuns.map((run) => (
          <div className="eval-run" key={run.at}>
            <b className={run.pass_rate === 1 ? 'ok' : ''}>{Math.round(run.pass_rate * 100)}%</b>
            <span>{run.passed}/{run.total} casos</span>
            <code>{new Date(run.at).toLocaleString('pt-BR')}</code>
          </div>
        ))}
      </div>
      <details className="raw-metrics"><summary>Ver payload técnico</summary><pre>{JSON.stringify(metrics, null, 2)}</pre></details>
    </section>
  );
}

export default function App() {
  const [nav, setNav] = useState('Chat');
  const [inspector, setInspector] = useState('agents');
  const [health, setHealth] = useState(null);
  const [customer, setCustomer] = useState(null);
  const [agents, setAgents] = useState([]);
  const [demoScenarios, setDemoScenarios] = useState([]);
  const [handoffs, setHandoffs] = useState([]);
  const [memory, setMemory] = useState([]);
  const [guardrails, setGuardrails] = useState([]);
  const [metrics, setMetrics] = useState({});
  const [messages, setMessages] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [conversationId, setConversationId] = useState(null);
  const [lastRun, setLastRun] = useState(null);
  const [adminMode, setAdminMode] = useState(false);
  const [liveEvents, setLiveEvents] = useState([]);
  const [liveOn, setLiveOn] = useState(false);
  const [evalRuns, setEvalRuns] = useState([]);

  const loadCore = async () => {
    const [h, a] = await Promise.all([api.health(), api.agents()]);
    setHealth(h); setAgents(a);
  };
  const switchIdentity = async (customerKey) => {
    try {
      const who = await api.login(customerKey); setCustomer(who); await loadCore();
      const [mem, gr, met, lastConv, scenarios] = await Promise.all([api.memory(who.customer_key), api.guardrails('events'), api.metrics(), api.latestConversation(), api.demoScenarios()]);
      setMemory(mem); setGuardrails(gr); setMetrics(met);
      setDemoScenarios(scenarios);
      setHandoffs([]);
      if (lastConv?.turns?.length) {
        setConversationId(lastConv.conversation_id);
        setMessages(lastConv.turns.map((turn) => ({ role: turn.role, agent: lastConv.active_agent, text: turn.content })));
        // sem isso a conversa retomada mostra o texto certo mas raio-x/esteira vazios — parece que o
        // multi-agent não rodou, quando só faltava recarregar o registro do último turno.
        setTimeline(lastConv.last_timeline || []);
        setLastRun(lastConv.last_timeline ? { active_agent: lastConv.active_agent, usage: lastConv.last_usage || {} } : null);
      } else {
        setConversationId(null); setMessages([]); setTimeline([]); setLastRun(null);
      }
    } catch (err) { setError(err.message); }
  };
  useEffect(() => { switchIdentity('ana'); }, []);

  useEffect(() => {
    if (nav === 'Métricas' && adminMode) {
      api.evalRuns().then(setEvalRuns).catch(() => setEvalRuns([]));
    }
  }, [nav, adminMode]);

  useEffect(() => {
    if (!customer) return undefined;
    const controller = new AbortController();
    let cancelled = false;
    const connect = async () => {
      while (!cancelled && !controller.signal.aborted) {
        try {
          setLiveOn(true);
          await api.streamEvents((event) => {
            setLiveEvents([{ ...event, receivedAt: Date.now() }]);
          }, controller.signal);
        } catch (err) {
          // conexão caiu (servidor reiniciou, rede oscilou) — reconecta em vez de ficar "offline" pra sempre
        }
        setLiveOn(false);
        if (!cancelled && !controller.signal.aborted) await new Promise((resolve) => setTimeout(resolve, 3000));
      }
    };
    connect();
    return () => { cancelled = true; controller.abort(); setLiveOn(false); };
  }, [customer?.customer_key]);

  const newConversation = () => {
    setConversationId(null); setMessages([]); setTimeline([]); setLastRun(null); setHandoffs([]); setInput('');
    setGuardrails([]); setMetrics({}); setLiveEvents([]);
  };

  const send = async () => {
    if (!input.trim() || busy) return;
    const value = input.trim(); setInput(''); setBusy(true); setError('');
    setMessages((items) => [...items, { role: 'user', text: value }]);
    try {
      const run = await api.chat(value, conversationId);
      setConversationId(run.conversation_id); setTimeline(run.timeline); setLastRun(run);
      const longTermUsed = (run.timeline || []).some((event) => event.collection === 'long_term_memory');
      setMessages((items) => [...items, { role: 'assistant', agent: run.active_agent, text: run.response, cacheHit: run.cache_hit, cacheSource: run.cache_source, tokens: run.usage?.total ?? 0, longTermUsed }]);
      const [hs, met, gr, mem] = await Promise.all([api.handoffs(run.conversation_id), api.metrics(), api.guardrails('events'), api.memory(customer.customer_key)]);
      setHandoffs(hs); setMetrics(met); setGuardrails(gr); setMemory(mem);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };

  const stats = useMemo(() => ({ agents: health?.counts?.agents ?? '—', handoffs: handoffs.length, route: lastRun?.route_source ?? '—', tokens: lastRun?.usage?.total ?? 0 }), [health, handoffs, lastRun]);

  const agentLabels = useMemo(() => Object.fromEntries(agents.map((agent) => [agent.agent_key, agent.label])), [agents]);
  const cast = useMemo(() => {
    const sequence = (timeline || [])
      .filter((event) => event.agent && event.category !== 'cache')
      .map((event) => event.agent);
    return sequence.filter((agent, index) => agent !== sequence[index - 1]);
  }, [timeline]);

  const data = { agents, handoffs, memory, guardrails, metrics, castKeys: cast };

  const collectionsTouched = useMemo(() => {
    const byCollection = new Map();
    for (const event of timeline || []) {
      if (!event.collection || !event.op) continue;
      if (!byCollection.has(event.collection)) byCollection.set(event.collection, []);
      byCollection.get(event.collection).push({ op: event.op, agent: event.agent, title: event.title });
    }
    return [...byCollection.entries()];
  }, [timeline]);

  return (
    <>
      <nav className="top-nav"><div className="nav-inner"><button className="brand" onClick={() => setNav('Chat')}><span className="leaf">◆</span><span>MongoDB</span><b>Agent Control Plane</b></button><div className="nav-tabs">{NAV.map((item) => <button className={nav === item ? 'active' : ''} key={item} onClick={() => setNav(item)}>{item}</button>)}</div><label className="identity-select">identidade<select value={customer?.customer_key || 'ana'} onChange={(event) => switchIdentity(event.target.value)}>{IDENTITIES.map((key) => <option key={key} value={key}>{key}</option>)}</select></label><div className="live-pill" title="Change Stream do MongoDB Atlas em agent_handoffs"><span className={liveOn ? 'ok' : ''} />{liveOn ? 'ao vivo' : 'offline'}</div><div className="health-pill"><span className={health ? 'ok' : ''} />{health ? `${health.storage} · ok` : 'conectando'}</div></div></nav>
      <main className="content">
        {error && <div className="error-banner">{error}<button onClick={() => setError('')}>×</button></div>}
        {nav === 'Chat' && <>
          <header className="hero"><div><div className="hero-kicker">PoV · arquitetura multi-agente</div><h1>A colaboração é uma <span>query.</span></h1><p>Cada decisão, ferramenta e handoff deixa um documento consultável no MongoDB.</p></div><div className="turn-state"><span>turno atual</span><code>{conversationId || 'aguardando mensagem'}</code><b>{lastRun?.active_agent || '—'}</b><button className="new-conversation-btn" onClick={newConversation} disabled={busy}>+ nova conversa</button></div></header>
          {cast.length > 0 && (
            <div className="agent-cast" title={lastRun?.route_source === 'fanout' ? 'Agentes despachados em paralelo (fan-out), não em cadeia' : 'Agentes que participaram deste turno, em ordem de atuação'}>
              <span className="agent-cast-label">{lastRun?.route_source === 'fanout' ? 'despacho paralelo' : 'agentes em ação'}</span>
              {cast.map((agentKey, index) => {
                const isFanout = lastRun?.route_source === 'fanout';
                const call = index > 0 && !isFanout ? handoffs.find((h) => h.from_agent === cast[index - 1] && h.to_agent === agentKey) : null;
                return (
                  <span className="agent-cast-item" key={`${agentKey}-${index}`}>
                    {index > 0 && (isFanout
                      ? <span className="agent-cast-arrow" title="rodou ao mesmo tempo, sem depender um do outro">+ (paralelo)</span>
                      : <span className="agent-cast-arrow" title={call ? `handoff: ${call.reason}` : 'handoff'}>chamou →</span>)}
                    <span className={`agent-cast-pill ${(lastRun?.active_agent || '').split('+').includes(agentKey) ? 'current' : ''}`}>{agentLabels[agentKey] || agentKey}</span>
                  </span>
                );
              })}
            </div>
          )}
          {collectionsTouched.length > 0 && (
            <div className="collections-panel" title="Collections do MongoDB tocadas neste turno, com o tipo de operação">
              <span className="collections-panel-label">coleções em ação neste turno</span>
              <div className="collections-panel-grid">
                {collectionsTouched.map(([collection, ops]) => (
                  <div className="collection-chip" key={collection}>
                    <code>{collection}</code>
                    <div className="collection-chip-ops">
                      {ops.map((item, index) => (
                        <span className={`op-badge op-${item.op}`} key={index} title={`${item.agent || 'orquestrador'} — ${item.title}`}>{OP_LABELS[item.op] || item.op}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className="stat-bar"><div><strong>{stats.agents}</strong><span>agentes ativos</span></div><div><strong>{stats.handoffs}</strong><span>handoffs no turno</span></div><div><strong className="small">{stats.route}</strong><span>origem da rota</span></div><div><strong>{stats.tokens}</strong><span>tokens estimados</span></div></div>
          {liveEvents.length > 0 && (
            <div className="live-feed">
              <div className="panel-label"><span>último handoff · agent_handoffs</span><code>change stream</code></div>
              {liveEvents.map((event, index) => (
                <div className="live-feed-item" key={`${event.at}-${index}`}>
                  <span className="teal-dot" />
                  <b>{event.from_agent}</b> → <b>{event.to_agent}</b>
                  <small>{event.reason}</small>
                </div>
              ))}
            </div>
          )}
          <div className="workspace"><ChatPanel key={customer?.customer_key} {...{ messages, input, setInput, send, busy }} customerName={customer?.name} demos={demoScenarios} /><section className="timeline-panel"><div className="panel-label"><span>raio-x do turno</span><code>{timeline.length} eventos</code></div><Timeline events={timeline} /></section><Inspector tab={inspector} {...data} /></div>
          <div className="inspector-tabs">{['agents', 'handoffs', 'memory', 'guardrails', 'metrics'].map((item) => <button className={inspector === item ? 'active' : ''} onClick={() => setInspector(item)} key={item}>{item}</button>)}</div>
        </>}
        {nav === 'Agentes' && <AgentsPage agents={agents} adminMode={adminMode} setAdminMode={setAdminMode} reload={loadCore} />}
        {nav === 'Guardrails' && <DataPage title="Segurança antes da inteligência." subtitle="Entrada é validada uma vez por turno, antes de qualquer modelo, memória ou trace.">{guardrails.length ? <pre>{JSON.stringify(guardrails, null, 2)}</pre> : <p className="inspector-empty">Nenhum evento ainda — só aparece aqui quando uma mensagem é de fato bloqueada. Tente o prompt de guardrail sugerido para a identidade Carla ou Diego.</p>}</DataPage>}
        {nav === 'Métricas' && <MetricsPage metrics={metrics} evalRuns={evalRuns} adminMode={adminMode} />}
      </main>
      <footer><span>MongoDB Atlas</span><code>multi_agent_poc + ai_brain</code><span>{customer?.name || 'identidade demo'}</span></footer>
    </>
  );
}
