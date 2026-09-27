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

export default function Admin() {
  const { user, loading, refresh } = useAuth("admin");
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState("");

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
    </main>
  );
}