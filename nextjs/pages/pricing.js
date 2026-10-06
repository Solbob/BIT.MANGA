import { useEffect, useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { SiteHeader } from "@/components/site-header";
import { Toast } from "@/components/toast";
import { apiFetch, signOut, useAuth } from "@/lib/api";

export default function Pricing() {
  const { user, loading, refresh } = useAuth();
  const [working, setWorking] = useState(false);
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [qrError, setQrError] = useState(false);
  const [toast, setToast] = useState("");
  const [error, setError] = useState(false);
  const paymentPlaceholderUrl = "https://www.google.com/search?q=BIT.MANGA+Premium+membership+payment";
  const qrImageUrl = `https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(paymentPlaceholderUrl)}`;

  async function handleSignOut() {
    await signOut();
    await refresh();
  }

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 3500);
    return () => clearTimeout(timer);
  }, [toast]);

  function openCheckout() {
    setQrError(false);
    setCheckoutOpen(true);
  }

  async function completeMockPayment() {
    setWorking(true);
    setError(false);
    try {
      await apiFetch("/checkout/mock", { method: "POST" });
      await refresh();
      setCheckoutOpen(false);
      setToast("Welcome to Premium. Every chapter is yours.");
    } catch (err) {
      setToast(err.message);
      setError(true);
    } finally {
      setWorking(false);
    }
  }

  if (loading || !user) return <main className="page-loading">Loading membership…</main>;
  return (
    <main className="app-page pricing-page">
      <SiteHeader user={user} onSignOut={handleSignOut} />
      <section className="pricing-heading"><p className="eyebrow">A LITTLE MORE STORY</p><h1>Choose how you<br /><em>want to read.</em></h1><p>Stay free, or open the door to every chapter.</p></section>
      <section className="plan-grid">
        <article className="plan-card free-plan">
          <div className="plan-top"><span className="plan-index">01 / STARTER</span><span className="plan-symbol">○</span></div>
          <h2>Free</h2><p className="plan-price">$0 <span>/ forever</span></p>
          <p className="plan-copy">A good place to begin. Read free stories and build a shelf of up to 20 series.</p>
          <ul><li>Free series and chapters</li><li>Save up to 20 series</li><li>Reading history</li></ul>
          {user.role === "free" ? <span className="current-plan">YOUR CURRENT PLAN</span> : <Button asChild variant="outline" className="w-full"><Link href="/reader">Explore free stories</Link></Button>}
        </article>
        <article className="plan-card premium-plan">
          <div className="plan-top"><span className="plan-index">02 / ALL ACCESS</span><span className="plan-symbol">✳</span></div>
          <h2>Premium</h2><p className="plan-price">$9.99 <span>/ 30 days</span></p>
          <p className="plan-copy">For readers who always want one more chapter. One simple membership, everything unlocked.</p>
          <ul><li>Every free and Premium chapter</li><li>Unlimited bookmarks</li><li>New chapters as they arrive</li></ul>
          {user.role === "premium" ? <span className="current-plan">YOU’RE A MEMBER</span> : user.role === "admin" ? <span className="current-plan">ADMIN ACCOUNTS DO NOT NEED A SUBSCRIPTION</span> : <Button className="w-full" onClick={openCheckout}>Upgrade to Premium · $9.99</Button>}
          <span className="checkout-note">Mock checkout · no real payment collected</span>
        </article>
      </section>
      <div className="pricing-foot"><span>Questions about your membership?</span><Link href="/profile">View your account →</Link></div>
      {checkoutOpen && (
        <div className="checkout-overlay" onClick={(event) => {
          if (event.target === event.currentTarget) setCheckoutOpen(false);
        }}>
          <section className="checkout-dialog" role="dialog" aria-modal="true" aria-labelledby="checkout-title">
            <button className="checkout-close" type="button" onClick={() => setCheckoutOpen(false)} aria-label="Close checkout">×</button>
            <p className="eyebrow">MOCK PAYMENT</p>
            <h2 id="checkout-title">Scan to upgrade</h2>
            <p className="checkout-description">Scan this QR code with your phone. This demo code opens a Google Search placeholder; no real payment will be collected.</p>
            {qrError ? <p className="checkout-qr-error" role="alert">The QR code could not be loaded. Please try again.</p> : <img className="checkout-qr" src={qrImageUrl} alt="QR code linking to a Google Search placeholder" onError={() => setQrError(true)} />}
            <a className="checkout-placeholder-link" href={paymentPlaceholderUrl} target="_blank" rel="noreferrer">View placeholder link</a>
            <Button className="w-full checkout-confirm" onClick={completeMockPayment} disabled={working}>{working ? "Completing mock checkout…" : "Complete mock payment"}</Button>
            <span className="checkout-note">Demo only · no real payment collected</span>
          </section>
        </div>
      )}
      <Toast message={toast} kind={error ? "error" : "success"} />
    </main>
  );
}