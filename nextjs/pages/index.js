import Link from "next/link";

import { Button } from "@/components/ui/button";
import { SiteHeader } from "@/components/site-header";

export default function Home() {
  return (
    <main className="landing-page">
      <SiteHeader />
      <section className="hero-shell">
        <div className="hero-copy">
          <p className="eyebrow"><span className="eyebrow-line" /> STORIES, FRAME BY FRAME</p>
          <h1>Turn the<br /><em>next page.</em></h1>
          <p className="hero-description">A better place to find your next favorite manga. Read a handpicked collection free, or go Premium for every chapter, every world.</p>
          <div className="hero-actions">
            <Button asChild size="default"><Link href="/reader">Explore the library <span aria-hidden="true">↗</span></Link></Button>
            <Link className="text-link" href="/pricing">See membership <span aria-hidden="true">→</span></Link>
          </div>
          <div className="hero-proof"><span className="proof-avatars">K&nbsp; M&nbsp; S</span><span>Made for readers, not endless scrolling.</span></div>
        </div>
        <div className="hero-art" aria-label="Featured manga collection">
          <div className="cover cover-back">
            <img src="https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?auto=format&fit=crop&w=720&q=85" alt="Sunrise over a misty mountain" />
            <span className="cover-label">BLUE<br />HOUR</span>
            <span className="cover-vertical">A STORY ABOUT BEGINNINGS</span>
          </div>
          <div className="cover cover-front">
            <img src="https://images.unsplash.com/photo-1519608487953-e999c86e7455?auto=format&fit=crop&w=720&q=85" alt="A night sky full of stars" />
            <span className="cover-stamp">ISSUE<br />01</span>
            <span className="cover-title">THE LAST<br /><i>LANTERN</i></span>
            <span className="cover-small">A TALE OF LIGHT & DISTANCE</span>
          </div>
          <div className="hero-note"><span className="note-star">✳</span><span>New chapters<br />every week</span></div>
          <div className="art-index">01 <span>/</span> 06</div>
        </div>
      </section>
      <section className="landing-bottom">
        <div className="section-kicker">YOUR NEXT OBSESSION STARTS HERE</div>
        <div className="value-columns">
          <article><span className="value-number">01</span><h2>Start anywhere.</h2><p>Find a new world in our always-growing library of independent stories.</p></article>
          <article><span className="value-number">02</span><h2>Read your way.</h2><p>Pick up where you left off, save a series, and keep your shelf close.</p></article>
          <article><span className="value-number">03</span><h2>Go all in.</h2><p>Free readers get plenty to love. Premium unlocks the whole collection.</p></article>
        </div>
        <div className="tier-strip"><span><strong>FREE</strong> · Start reading today</span><span><strong>PREMIUM</strong> · All chapters, one membership</span><Button asChild variant="outline" size="sm"><Link href="/pricing">Compare plans</Link></Button></div>
      </section>
    </main>
  );
}
