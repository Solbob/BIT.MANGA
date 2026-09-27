import Link from "next/link";

import { Button } from "@/components/ui/button";

export function SiteHeader({ user, onSignOut }) {
  return (
    <header className="site-header">
      <Link href="/" className="brand-lockup" aria-label="Bit Manga home">
        <span className="brand-mark">B.</span>
        <span>BIT<span className="brand-light">.MANGA</span></span>
      </Link>
      <nav className="site-nav" aria-label="Main navigation">
        <Link href="/reader">Discover</Link>
        <Link href="/pricing">Membership</Link>
        {user && <Link href="/profile">My library</Link>}
        {user?.role === "admin" && <Link href="/admin">Analytics</Link>}
      </nav>
      <div className="header-action">
        {user ? (
          <>
            <span className="header-user">{user.email}</span>
            <Button variant="outline" size="sm" onClick={onSignOut}>Sign out</Button>
          </>
        ) : (
          <Button asChild size="sm"><Link href="/login">Log in</Link></Button>
        )}
      </div>
    </header>
  );
}