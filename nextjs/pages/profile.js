import { useEffect, useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { SiteHeader } from "@/components/site-header";
import { Toast } from "@/components/toast";
import { apiFetch, signOut, useAuth } from "@/lib/api";

export default function Profile() {
  const { user, loading, refresh } = useAuth();
  const [bookmarks, setBookmarks] = useState([]);
  const [toast, setToast] = useState("");

  useEffect(() => {
    if (!user) return;
    apiFetch("/bookmarks").then(setBookmarks).catch((err) => setToast(err.message));
  }, [user]);

  async function removeBookmark(id) {
    try {
      await apiFetch(`/bookmarks/${id}`, { method: "DELETE" });
      setBookmarks((current) => current.filter((item) => item.id !== id));
      setToast("Removed from your library.");
    } catch (err) {
      setToast(err.message);
    }
  }

  if (loading || !user) return <main className="page-loading">Loading your library…</main>;
  return (
    <main className="app-page">
      <SiteHeader user={user} onSignOut={() => { signOut(); refresh(); }} />
      <section className="page-heading profile-heading"><div><p className="eyebrow">YOUR ACCOUNT</p><h1>Your reading <em>shelf.</em></h1></div><span className={`tier-pill tier-${user.role}`}>{user.role}</span></section>
      <section className="profile-grid">
        <aside className="profile-summary">
          <span className="profile-monogram">{user.email.slice(0, 1).toUpperCase()}</span>
          <h2>{user.email}</h2>
          <span className={`role-label role-${user.role}`}>{user.role} member</span>
          <div className="profile-rule" />
          <div className="profile-data"><span>MEMBER SINCE</span><strong>{new Date(user.created_at).toLocaleDateString(undefined, { month: "long", year: "numeric" })}</strong></div>
          <div className="profile-data"><span>BOOKMARKS</span><strong>{bookmarks.length}{user.role === "free" ? " / 20" : " / unlimited"}</strong></div>
          {user.subscription && <div className="profile-data"><span>MEMBERSHIP RENEWS</span><strong>{new Date(user.subscription.expires_at).toLocaleDateString()}</strong></div>}
          {user.role === "free" && <Button asChild className="w-full profile-upgrade"><Link href="/pricing">Explore Premium ↗</Link></Button>}
          {user.role === "admin" && <Button asChild variant="outline" className="w-full"><Link href="/admin">Open analytics</Link></Button>}
        </aside>
        <div className="profile-library">
          <div className="catalog-toolbar profile-toolbar"><div><p className="eyebrow">PICK UP WHERE YOU LEFT OFF</p><h2>Saved stories</h2></div><Link className="text-link" href="/reader">Discover more ↗</Link></div>
          {!bookmarks.length ? <div className="profile-empty"><span className="empty-mark">↗</span><h3>Your shelf is waiting.</h3><p>Save a series while you browse and it will show up here.</p><Button asChild variant="outline"><Link href="/reader">Browse the library</Link></Button></div> : <div className="bookmark-list">
            {bookmarks.map((item) => <article className="bookmark-item" key={item.id}>
              <img src={item.cover_image} alt="" loading="lazy" />
              <div className="bookmark-details"><span className="eyebrow">{item.is_premium ? "PREMIUM SERIES" : "YOUR LIBRARY"}</span><h3>{item.title}</h3><p>{item.last_read_chapter_number ? `Last read: chapter ${item.last_read_chapter_number} · ${item.last_read_chapter_title}` : "Saved to your reading list"}</p></div>
              <div className="bookmark-actions">{item.last_read_chapter_id && <Button asChild size="sm"><Link href="/reader">Continue ↗</Link></Button>}<button type="button" className="icon-button" title="Remove bookmark" aria-label={`Remove ${item.title} from bookmarks`} onClick={() => removeBookmark(item.id)}>×</button></div>
            </article>)}
          </div>}
        </div>
      </section>
      <Toast message={toast} />
    </main>
  );
}