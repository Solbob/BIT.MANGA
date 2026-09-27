import { useEffect, useState } from "react";

import { SiteHeader } from "@/components/site-header";
import { Toast } from "@/components/toast";
import { apiFetch, signOut, useAuth } from "@/lib/api";

function LineChart({ rows }) {
  const values = rows.map((row) => Number(row.mrr));
  const max = Math.max(...values, 10);
  const points = values.map((value, index) => {
    const x = values.length < 2 ? 50 : 8 + (index / (values.length - 1)) * 84;
    const y = 88 - (value / max) * 72;
    return `${x},${y}`;
  }).join(" ");
  return <div className="chart-frame">
    {!rows.length ? <p className="empty-state">No membership data yet.</p> : <svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="Monthly recurring revenue trend">
      <line x1="8" x2="92" y1="88" y2="88" className="chart-axis" />
      <line x1="8" x2="92" y1="52" y2="52" className="chart-gridline" />
      <line x1="8" x2="92" y1="16" y2="16" className="chart-gridline" />
      <polyline points={points} className="chart-line" />
      {values.map((value, index) => {
        const x = values.length < 2 ? 50 : 8 + (index / (values.length - 1)) * 84;
        const y = 88 - (value / max) * 72;
        return <circle key={`${rows[index].month}-${index}`} cx={x} cy={y} r="1.5" className="chart-point"><title>{rows[index].month}: ${value.toFixed(2)}</title></circle>;
      })}
    </svg>}
    <div className="chart-labels">{rows.map((row) => <span key={row.month}>{row.month}</span>)}</div>
  </div>;
}

function SignupChart({ rows }) {
  const max = Math.max(...rows.map((row) => Number(row.free) + Number(row.premium) + Number(row.admin)), 1);
  return <div className="signup-chart">
    {!rows.length ? <p className="empty-state">No signup data yet.</p> : rows.map((row) => {
      const freeWidth = Number(row.free) / max * 100;
      const premiumWidth = Number(row.premium) / max * 100;
      const adminWidth = Number(row.admin) / max * 100;
      return <div className="signup-row" key={row.month}>
        <span className="signup-month">{row.month}</span>
        <div className="signup-bars" aria-label={`${row.free} free, ${row.premium} premium, ${row.admin} admin signups`}><span className="signup-free" style={{ width: `${freeWidth}%` }} /><span className="signup-premium" style={{ width: `${premiumWidth}%` }} /><span className="signup-admin" style={{ width: `${adminWidth}%` }} /></div>
        <strong>{Number(row.free) + Number(row.premium) + Number(row.admin)}</strong>
      </div>;
    })}
    <div className="chart-legend"><span><i className="legend-free" />Free</span><span><i className="legend-premium" />Premium</span><span><i className="legend-admin" />Admin</span></div>
  </div>;
}

function TransactionChart({ rows }) {
  const max = Math.max(...rows.map((row) => Number(row.transaction_volume)), 1);
  const money = (value) => new Intl.NumberFormat(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value || 0);
  return <div className="transaction-chart">
    {!rows.length ? <p className="empty-state">No transaction data yet.</p> : rows.map((row) => <div className="transaction-row" key={row.month}>
      <div className="transaction-month"><strong>{row.month}</strong><span>{row.transaction_count} payment{Number(row.transaction_count) === 1 ? "" : "s"}</span></div>
      <div className="transaction-bar"><span style={{ width: `${Number(row.transaction_volume) / max * 100}%` }} /></div>
      <strong className="transaction-total">{money(row.transaction_volume)}</strong>
    </div>)}
  </div>;
}

function UserManagement({ currentUserId }) {
  const [users, setUsers] = useState([]);
  const [search, setSearch] = useState("");
  const [editor, setEditor] = useState(null);
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let currentRequest = true;
    const timer = setTimeout(() => {
      setLoadingUsers(true);
      setError("");
      apiFetch(`/admin/users?search=${encodeURIComponent(search)}`)
        .then((rows) => { if (currentRequest) setUsers(rows); })
        .catch((err) => { if (currentRequest) setError(err.message); })
        .finally(() => { if (currentRequest) setLoadingUsers(false); });
    }, 200);
    return () => { currentRequest = false; clearTimeout(timer); };
  }, [search]);

  function startCreate() {
    setNotice("");
    setError("");
    setEditor({ mode: "create", email: "", password: "", role: "free" });
  }

  function startEdit(account) {
    setNotice("");
    setError("");
    setEditor({ mode: "edit", id: account.id, email: account.email, password: "", role: account.role });
  }

  async function reloadUsers() {
    const rows = await apiFetch(`/admin/users?search=${encodeURIComponent(search)}`);
    setUsers(rows);
  }

  async function saveUser(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    const payload = { email: editor.email, role: editor.role };
    if (editor.password) payload.password = editor.password;
    try {
      await apiFetch(editor.mode === "create" ? "/admin/users" : `/admin/users/${editor.id}`, {
        method: editor.mode === "create" ? "POST" : "PATCH",
        body: JSON.stringify(payload),
      });
      await reloadUsers();
      setEditor(null);
      setNotice(editor.mode === "create" ? "Account created." : "Account updated. Active sessions were revoked.");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function deleteUser(account) {
    if (!window.confirm(`Delete ${account.email}? This also removes their bookmarks and payment history.`)) return;
    setError("");
    setNotice("");
    try {
      await apiFetch(`/admin/users/${account.id}`, { method: "DELETE" });
      await reloadUsers();
      setNotice(`${account.email} was deleted.`);
    } catch (err) {
      setError(err.message);
    }
  }

  function formatDate(value) {
    if (!value) return "Never";
    return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  }

  return <section className="user-management" aria-labelledby="user-management-title">
    <div className="user-management-heading">
      <div><p className="eyebrow">ACCOUNT DIRECTORY</p><h2 id="user-management-title">People</h2></div>
      <button className="user-primary-action" type="button" onClick={startCreate}>＋ Add account</button>
    </div>

    {notice && <p className="user-notice" role="status">{notice}</p>}
    {error && <p className="user-error" role="alert">{error}</p>}

    {editor && <form className="user-editor" onSubmit={saveUser}>
      <div className="user-editor-heading"><div><span className="eyebrow">{editor.mode === "create" ? "NEW ACCOUNT" : `ACCOUNT · #${editor.id}`}</span><h3>{editor.mode === "create" ? "Create an account" : "Edit account"}</h3></div><button className="user-close-action" type="button" onClick={() => setEditor(null)} aria-label="Close account form">×</button></div>
      <label className="user-field">Email<input type="email" autoComplete="email" required maxLength={255} value={editor.email} onChange={(event) => setEditor({ ...editor, email: event.target.value })} /></label>
      <label className="user-field">Tier<select value={editor.role} onChange={(event) => setEditor({ ...editor, role: event.target.value })}><option value="free">Free</option><option value="premium">Premium · 30 days</option><option value="admin">Admin</option></select></label>
      <label className="user-field user-password-field">{editor.mode === "create" ? "Password" : "Reset password"}<input type="password" autoComplete="new-password" minLength={8} maxLength={128} required={editor.mode === "create"} value={editor.password} onChange={(event) => setEditor({ ...editor, password: event.target.value })} placeholder={editor.mode === "edit" ? "Leave blank to keep current password" : "At least 8 characters"} /></label>
      <div className="user-editor-actions"><button className="user-primary-action" type="submit" disabled={saving}>{saving ? "Saving…" : editor.mode === "create" ? "Create account" : "Save changes"}</button><button className="user-secondary-action" type="button" onClick={() => setEditor(null)} disabled={saving}>Cancel</button></div>
      <p className="user-editor-note">New or expired Premium access is set for 30 days; active access keeps its current expiry. Account changes revoke existing sessions.</p>
    </form>}

    <div className="user-directory-tools"><label htmlFor="user-search">Search accounts</label><input id="user-search" type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Email address or account ID" /><span>{users.length} shown · up to 200 accounts</span></div>
    <div className="user-table-wrap"><table className="user-table"><thead><tr><th>Account</th><th>Tier</th><th>Subscription</th><th>Joined</th><th>Last active</th><th><span className="visually-hidden">Actions</span></th></tr></thead><tbody>
      {loadingUsers ? <tr><td colSpan="6" className="user-table-message">Loading accounts…</td></tr> : users.length ? users.map((account) => {
        const isSelf = Number(account.id) === Number(currentUserId);
        return <tr key={account.id}>
          <td><strong>{account.email}</strong><small>Account #{account.id}{isSelf ? " · You" : ""}</small></td>
          <td><span className={`user-tier user-tier-${account.role}`}>{account.role}</span></td>
          <td>{account.subscription_status ? <span className="user-subscription">{account.subscription_status}<small>{formatDate(account.subscription_expires_at)}</small></span> : <span className="user-muted">—</span>}</td>
          <td>{formatDate(account.created_at)}</td><td>{formatDate(account.last_active_at)}</td>
          <td><div className="user-row-actions"><button type="button" className="user-row-action" onClick={() => startEdit(account)} disabled={isSelf} title={isSelf ? "Your account cannot be managed here" : `Edit ${account.email}`}>Edit</button><button type="button" className="user-row-action user-delete-action" onClick={() => deleteUser(account)} disabled={isSelf} title={isSelf ? "Your account cannot be deleted here" : `Delete ${account.email}`}>Delete</button></div></td>
        </tr>;
      }) : <tr><td colSpan="6" className="user-table-message">No accounts match this search.</td></tr>}
    </tbody></table></div>
    <p className="user-directory-footnote">Deleting an account permanently cascades to its bookmarks, subscriptions, and transactions. The current admin and final admin are protected.</p>
  </section>;
}

export default function Admin() {
  const { user, loading, refresh } = useAuth("admin");
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("overview");

  async function handleSignOut() {
    await signOut();
    await refresh();
  }

  useEffect(() => {
    if (!user || user.role !== "admin") return;
    apiFetch("/admin/metrics").then(setMetrics).catch((err) => setError(err.message));
  }, [user]);

  if (loading || !user || user.role !== "admin") return <main className="page-loading">Loading analytics…</main>;
  const money = (value) => new Intl.NumberFormat(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value || 0);
  return (
    <main className="app-page admin-page">
      <SiteHeader user={user} onSignOut={handleSignOut} />
      <section className="page-heading admin-heading"><div><p className="eyebrow">THE BIG PICTURE</p><h1>Reader <em>signals.</em></h1></div><span className="report-date">UPDATED {metrics ? new Date(metrics.as_of).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }).toUpperCase() : "—"}</span></section>
      <nav className="admin-tabs" aria-label="Admin sections"><button type="button" className={activeTab === "overview" ? "admin-tab admin-tab-active" : "admin-tab"} aria-current={activeTab === "overview" ? "page" : undefined} onClick={() => setActiveTab("overview")}>Overview</button><button type="button" className={activeTab === "users" ? "admin-tab admin-tab-active" : "admin-tab"} aria-current={activeTab === "users" ? "page" : undefined} onClick={() => setActiveTab("users")}>People</button></nav>
      {activeTab === "users" ? <UserManagement currentUserId={user.id} /> : <>
      {error && <Toast message={error} kind="error" />}
      {metrics && <>
        <section className="kpi-grid" aria-label="Key metrics">
          <article className="kpi-cell"><span>ACTIVE READERS · 30 DAYS</span><strong>{metrics.active_users.toLocaleString()}</strong><small>of {metrics.total_users.toLocaleString()} total accounts</small></article>
          <article className="kpi-cell"><span>TRANSACTION VOLUME</span><strong>{money(metrics.transaction_volume)}</strong><small>{metrics.transaction_count} successful payments</small></article>
          <article className="kpi-cell"><span>PROJECTED MRR / ARR</span><strong>{money(metrics.projected_mrr)}<i> MRR</i></strong><small>{money(metrics.projected_arr)} annualized</small></article>
          <article className="kpi-cell"><span>FREE → PREMIUM</span><strong>{metrics.conversion_rate}<i>%</i></strong><small>{metrics.premium_users} Premium readers</small></article>
        </section>
        <section className="analytics-grid">
          <article className="analytics-panel"><div className="analytics-panel-head"><div><span className="eyebrow">RECURRING REVENUE</span><h2>MRR over time</h2></div><span className="chart-period">LAST 6 MONTHS</span></div><div className="chart-amount">{money(metrics.projected_mrr)}<span> current run rate</span></div><LineChart rows={metrics.mrr_trend} /></article>
          <article className="analytics-panel signup-panel"><div className="analytics-panel-head"><div><span className="eyebrow">NEW READERS</span><h2>Signups by tier</h2></div><span className="chart-period">MONTHLY</span></div><SignupChart rows={metrics.signups_by_tier} /></article>
          <article className="analytics-panel transaction-panel"><div className="analytics-panel-head"><div><span className="eyebrow">SUCCESSFUL PAYMENTS</span><h2>Transaction volume</h2></div><span className="chart-period">COUNT + AMOUNT · 6 MONTHS</span></div><TransactionChart rows={metrics.transaction_trend} /></article>
        </section>
        <div className="analytics-note"><span className="note-star">✳</span><p>MRR is estimated at $9.99 per active subscription. Conversion is Premium accounts divided by all accounts.</p></div>
      </>}
      {!metrics && !error && <div className="page-loading">Loading your report…</div>}
      </>}
    </main>
  );
}