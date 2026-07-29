import { useEffect, useRef, useState } from "react";
import {
  api,
  money,
  type Account,
  type CategorySpend,
  type ChatMessage,
  type NetWorth,
  type Txn,
} from "./api.js";

export function App() {
  const [linked, setLinked] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [accounts, setAccounts] = useState<Account[]>([]);
  const [txns, setTxns] = useState<Txn[]>([]);
  const [spending, setSpending] = useState<{ totalSpend: number; categories: CategorySpend[] } | null>(null);
  const [nw, setNw] = useState<NetWorth | null>(null);

  // --- AI chat state ---
  const [chat, setChat] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat, chatBusy]);

  async function sendChat(e?: React.FormEvent) {
    e?.preventDefault();
    const text = input.trim();
    if (!text || chatBusy) return;
    setChatError(null);
    const next = [...chat, { role: "user", content: text }];
    setChat(next);
    setInput("");
    setChatBusy(true);
    try {
      const res = await api.chat(next);
      setChat(res.messages);
    } catch (err: any) {
      setChatError(err.message ?? "Chat failed");
      setChat(chat); // roll back the optimistic user message on failure
    } finally {
      setChatBusy(false);
    }
  }

  const visibleChat = chat.filter(
    (m) => (m.role === "user" || m.role === "assistant") && m.content
  );

  useEffect(() => {
    api.health().then((h) => setLinked(h.linked)).catch(() => {});
  }, []);

  async function loadAll() {
    setLoading(true);
    setError(null);
    try {
      const [acc, tx, sp, netw] = await Promise.all([
        api.accounts(),
        api.transactions({ count: 50 }),
        api.spending(),
        api.netWorth(),
      ]);
      setAccounts(acc.accounts);
      setTxns(tx.transactions);
      setSpending(sp);
      setNw(netw);
    } catch (e: any) {
      setError(e.message ?? "Failed to load data");
    } finally {
      setLoading(false);
    }
  }

  async function connect() {
    setLoading(true);
    setError(null);
    try {
      await api.connect();
      setLinked(true);
      await loadAll();
    } catch (e: any) {
      setError(e.message ?? "Connect failed. Check server .env has Plaid sandbox credentials.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (linked) loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [linked]);

  const maxCat = spending?.categories[0]?.total ?? 1;

  return (
    <div className="app">
      <header>
        <h1>🏦 Banking Copilot</h1>
        <span className="badge">Plaid Sandbox · read-only</span>
      </header>

      <div className="toolbar">
        <button className="primary" onClick={connect} disabled={loading}>
          {linked ? "Reconnect sandbox" : "Connect Plaid sandbox"}
        </button>
        {linked && (
          <button onClick={loadAll} disabled={loading}>
            Refresh
          </button>
        )}
        {loading && <span className="muted">Loading…</span>}
      </div>

      {error && <div className="error">⚠️ {error}</div>}

      {!linked && !loading && (
        <div className="empty">
          <p>No account linked yet.</p>
          <p className="muted">
            Click <strong>Connect Plaid sandbox</strong> to bootstrap a demo bank
            (checking, savings, credit card) and pull transactions.
          </p>
        </div>
      )}

      {linked && (
        <>
          {nw && (
            <section className="networth">
              <div className="nw-card asset">
                <span>Assets</span>
                <strong>{money(nw.assets)}</strong>
              </div>
              <div className="nw-card liability">
                <span>Liabilities</span>
                <strong>{money(nw.liabilities)}</strong>
              </div>
              <div className="nw-card total">
                <span>Net Worth</span>
                <strong>{money(nw.netWorth)}</strong>
              </div>
            </section>
          )}

          <section>
            <h2>Accounts</h2>
            <div className="accounts">
              {accounts.map((a) => (
                <div key={a.accountId} className={`account ${a.type}`}>
                  <div className="account-head">
                    <strong>{a.name}</strong>
                    <span className="mask">••{a.mask ?? "----"}</span>
                  </div>
                  <div className="account-type">
                    {a.subtype ?? a.type}
                  </div>
                  <div className="account-bal">{money(a.currentBalance, a.currency ?? "USD")}</div>
                  {a.creditLimit != null && (
                    <div className="muted small">
                      Limit {money(a.creditLimit, a.currency ?? "USD")} ·{" "}
                      {Math.round(((a.currentBalance ?? 0) / a.creditLimit) * 100)}% used
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>

          <div className="grid">
            <section>
              <h2>Spending by category</h2>
              {spending && (
                <>
                  <p className="muted">
                    Total spend: <strong>{money(spending.totalSpend)}</strong>{" "}
                    <span className="small">(transfers &amp; card payments excluded)</span>
                  </p>
                  <ul className="bars">
                    {spending.categories.map((c) => (
                      <li key={c.category}>
                        <span className="bar-label">{c.category}</span>
                        <span className="bar-track">
                          <span
                            className="bar-fill"
                            style={{ width: `${(c.total / maxCat) * 100}%` }}
                          />
                        </span>
                        <span className="bar-value">{money(c.total)}</span>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </section>

            <section>
              <h2>Recent transactions</h2>
              <table className="txns">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Name</th>
                    <th>Category</th>
                    <th className="right">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {txns.map((t) => (
                    <tr key={t.id}>
                      <td className="muted small">{t.date}</td>
                      <td>{t.merchant ?? t.name}</td>
                      <td className="small">
                        {t.category}
                        {t.isTransfer && <span className="pill">transfer</span>}
                      </td>
                      <td className={`right ${t.direction}`}>
                        {t.direction === "outflow" ? "-" : "+"}
                        {money(t.amount)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </div>

          <section className="chat">
            <h2>💬 Ask Banking Copilot</h2>
            <p className="muted small">
              Powered by Azure AI Foundry · answers are grounded in your real
              account data via tool calls.
            </p>
            <div className="chat-log">
              {visibleChat.length === 0 && !chatBusy && (
                <div className="chat-hint muted">
                  Try: “How much did I spend this month?”, “What’s my net worth?”,
                  or “How much on dining?”
                </div>
              )}
              {visibleChat.map((m, i) => (
                <div key={i} className={`chat-msg ${m.role}`}>
                  <span className="chat-role">
                    {m.role === "user" ? "You" : "Copilot"}
                  </span>
                  <div className="chat-bubble">{m.content}</div>
                </div>
              ))}
              {chatBusy && (
                <div className="chat-msg assistant">
                  <span className="chat-role">Copilot</span>
                  <div className="chat-bubble typing">thinking…</div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
            {chatError && <div className="error">⚠️ {chatError}</div>}
            <form className="chat-input" onSubmit={sendChat}>
              <input
                type="text"
                placeholder="Ask about your spending, accounts, or net worth…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={chatBusy}
              />
              <button className="primary" type="submit" disabled={chatBusy || !input.trim()}>
                Send
              </button>
            </form>
          </section>
        </>
      )}
    </div>
  );
}
