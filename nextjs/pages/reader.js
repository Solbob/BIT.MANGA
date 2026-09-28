import { useEffect, useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SiteHeader } from "@/components/site-header";
import { Toast } from "@/components/toast";
import { apiFetch, signOut, useAuth } from "@/lib/api";

export default function Reader() {
  const { user, loading, refresh } = useAuth();
  const [series, setSeries] = useState([]);
  const [selected, setSelected] = useState(null);
  const [chapters, setChapters] = useState([]);
  const [chapter, setChapter] = useState(null);
  const [readerMinimized, setReaderMinimized] = useState(false);
  const [search, setSearch] = useState("");
  const [toast, setToast] = useState("");
  const [error, setError] = useState("");
  const [form, setForm] = useState({ title: "", description: "", cover_image: "", is_premium: false });
  const [chapterForm, setChapterForm] = useState({ number: 1, title: "", content: "" });
  const [editingChapter, setEditingChapter] = useState(null);

  async function handleSignOut() {
    await signOut();
    await refresh();
  }

  useEffect(() => {
    if (!user) return;
    apiFetch("/series").then(setSeries).catch((err) => setError(err.message));
  }, [user]);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 3200);
    return () => clearTimeout(timer);
  }, [toast]);

  async function openSeries(item) {
    setSelected(item);
    setChapter(null);
    setReaderMinimized(false);
    try {
      setChapters(await apiFetch(`/series/${item.id}/chapters`));
    } catch (err) {
      setToast(err.message);
    }
  }

  async function openChapter(item) {
    try {
      const data = await apiFetch(`/chapters/${item.id}`);
      setChapter(data);
      setReaderMinimized(false);
      await apiFetch("/bookmarks", {
        method: "POST",
        body: JSON.stringify({ series_id: item.series_id, last_read_chapter_id: item.id }),
      });
    } catch (err) {
      if (err.message.toLowerCase().includes("premium")) {
        setToast("That chapter is for Premium members.");
      } else {
        setToast(err.message);
      }
    }
  }

  async function saveBookmark() {
    try {
      await apiFetch("/bookmarks", { method: "POST", body: JSON.stringify({ series_id: selected.id }) });
      setToast("Added to your library.");
    } catch (err) {
      setToast(err.message);
    }
  }

  async function createSeries(event) {
    event.preventDefault();
    try {
      const created = await apiFetch("/series", { method: "POST", body: JSON.stringify(form) });
      setSeries((current) => [created, ...current]);
      setForm({ title: "", description: "", cover_image: "", is_premium: false });
      setToast("Series created.");
    } catch (err) {
      setToast(err.message);
    }
  }

  async function deleteSelectedSeries() {
    if (!selected) return;
    try {
      await apiFetch(`/series/${selected.id}`, { method: "DELETE" });
      setSeries((current) => current.filter((item) => item.id !== selected.id));
      setSelected(null);
      setChapter(null);
      setReaderMinimized(false);
      setChapters([]);
      setToast("Series deleted.");
    } catch (err) {
      setToast(err.message);
    }
  }

  async function saveChapter(event) {
    event.preventDefault();
    if (!selected) return;
    const payload = {
      number: Number(chapterForm.number),
      title: chapterForm.title,
      content: chapterForm.content.split("\n").map((value) => value.trim()).filter(Boolean),
    };
    try {
      if (editingChapter) {
        await apiFetch(`/chapters/${editingChapter}`, { method: "PATCH", body: JSON.stringify(payload) });
        setToast("Chapter updated.");
      } else {
        await apiFetch("/chapters", { method: "POST", body: JSON.stringify({ ...payload, series_id: selected.id }) });
        setToast("Chapter added.");
      }
      setEditingChapter(null);
      setChapterForm({ number: chapters.length + 2, title: "", content: "" });
      setChapters(await apiFetch(`/series/${selected.id}/chapters`));
    } catch (err) {
      setToast(err.message);
    }
  }

  async function editChapter(item) {
    try {
      const data = await apiFetch(`/chapters/${item.id}`);
      setEditingChapter(item.id);
      setChapterForm({ number: data.number, title: data.title, content: data.content.join("\n") });
    } catch (err) {
      setToast(err.message);
    }
  }

  async function deleteChapter(item) {
    try {
      await apiFetch(`/chapters/${item.id}`, { method: "DELETE" });
      setChapters((current) => current.filter((chapterItem) => chapterItem.id !== item.id));
      if (chapter?.id === item.id) setChapter(null);
      setToast("Chapter deleted.");
    } catch (err) {
      setToast(err.message);
    }
  }

  if (loading || !user) return <main className="page-loading">Opening your library…</main>;
  const visibleSeries = series.filter((item) => item.title.toLowerCase().includes(search.toLowerCase()));

  return (
    <main className="app-page">
      <SiteHeader user={user} onSignOut={handleSignOut} />
      <section className="page-heading">
        <div><p className="eyebrow">THE READING ROOM</p><h1>Find your next <em>world.</em></h1></div>
        <div className="reader-intro"><span className="tier-pill">{user.role}</span><span>Stories worth staying up for.</span></div>
      </section>

      <section className="library-layout">
        <div className="catalog-pane">
          <div className="catalog-toolbar"><div><h2>Explore series</h2><span>{series.length} stories in the library</span></div><Input aria-label="Search series" placeholder="Search titles…" value={search} onChange={(event) => setSearch(event.target.value)} className="search-input" /></div>
          {error && <p className="form-error">{error}</p>}
          <div className="series-grid">
            {visibleSeries.map((item, index) => (
              <button type="button" key={item.id} onClick={() => openSeries(item)} className={`series-tile ${selected?.id === item.id ? "series-selected" : ""}`}>
                <span className={`series-art series-art-${index % 3}`}><img src={item.cover_image} alt="" loading="lazy" />{item.is_premium && <span className="cover-badge">PREMIUM</span>}<span className="series-art-index">{String(index + 1).padStart(2, "0")}</span></span>
                <span className="series-title-row"><strong>{item.title}</strong><span>{item.is_premium ? "✳" : "↗"}</span></span>
                <span className="series-meta">{item.chapter_count || 1} chapter{item.chapter_count === 1 ? "" : "s"} · {item.is_premium ? "Member story" : "Free to read"}</span>
              </button>
            ))}
          </div>
          {!visibleSeries.length && <p className="empty-state">No series match that title.</p>}

          {user.role === "admin" && <form className="admin-create-form" onSubmit={createSeries}>
            <div><p className="eyebrow">LIBRARY MANAGEMENT</p><h3>Add a series</h3></div>
            <Input placeholder="Series title" value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} required />
            <Input placeholder="Short description" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
            <Input placeholder="Cover image URL" value={form.cover_image} onChange={(event) => setForm({ ...form, cover_image: event.target.value })} />
            <label className="checkbox-line"><input type="checkbox" checked={form.is_premium} onChange={(event) => setForm({ ...form, is_premium: event.target.checked })} /> Premium series</label>
            <Button type="submit" size="sm">Add series</Button>
          </form>}
          {chapter && !readerMinimized && <div className="chapter-reader chapter-reader-overlay">
            <div className="reader-chapter-head"><div><span>NOW READING</span><h3>{chapter.title}</h3></div><div className="reader-chapter-controls"><button type="button" onClick={() => setReaderMinimized(true)} aria-label="Minimize reader" title="Show Explore series">−</button><button type="button" onClick={() => setChapter(null)} aria-label="Close chapter" title="Close chapter">×</button></div></div>
            <div className="reader-pages">{chapter.content.map((image, index) => <img key={`${chapter.id}-${index}`} src={image} alt={`Page ${index + 1}`} loading={index > 1 ? "lazy" : "eager"} />)}</div>
          </div>}
        </div>

        <aside className="detail-pane">
          {!selected ? <div className="reader-empty"><span className="empty-mark">✳</span><p>Pick a series<br />to see its chapters.</p><span>YOUR NEXT READ IS HERE</span></div> : <>
            <div className="detail-topline"><span>SELECTED SERIES</span>{selected.is_premium && <span className="premium-label">PREMIUM</span>}</div>
            <h2 className="detail-title">{selected.title}</h2>
            <p className="detail-description">{selected.description}</p>
            <div className="detail-actions"><Button variant="outline" size="sm" onClick={saveBookmark}>＋ Save to library</Button>{user.role === "admin" && <Button variant="outline" size="sm" onClick={deleteSelectedSeries}>Delete series</Button>}</div>
            {chapter && readerMinimized && <Button className="reader-resume" variant="outline" size="sm" onClick={() => setReaderMinimized(false)}>Resume reading</Button>}
            <div className="chapter-list-head"><span>CHAPTERS</span><span>{chapters.length} available</span></div>
            <div className="chapter-list">{chapters.map((item) => {
              const locked = selected.is_premium && user.role === "free";
              return <div className="chapter-row" key={item.id}>
                <button type="button" disabled={locked} onClick={() => openChapter(item)} className="chapter-open"><span className="chapter-number">{String(item.number).padStart(2, "0")}</span><span><strong>{item.title}</strong><small>Chapter {item.number}</small></span></button>
                {locked ? <Link className="unlock-link" href="/pricing">Unlock ↗</Link> : user.role === "admin" ? <span className="chapter-admin-actions"><button type="button" onClick={() => editChapter(item)} title="Edit chapter" aria-label={`Edit chapter ${item.number}`}>✎</button><button type="button" onClick={() => deleteChapter(item)} title="Delete chapter" aria-label={`Delete chapter ${item.number}`}>×</button></span> : <span className="chapter-arrow">↗</span>}
              </div>;
            })}</div>
            {user.role === "admin" && <form className="chapter-admin-form" onSubmit={saveChapter}>
              <div className="chapter-admin-title"><span className="eyebrow">{editingChapter ? "EDIT CHAPTER" : "ADD A CHAPTER"}</span>{editingChapter && <button type="button" onClick={() => { setEditingChapter(null); setChapterForm({ number: chapters.length + 1, title: "", content: "" }); }}>Cancel</button>}</div>
              <div className="chapter-form-row"><Input aria-label="Chapter number" type="number" min="1" value={chapterForm.number} onChange={(event) => setChapterForm({ ...chapterForm, number: event.target.value })} required /><Input aria-label="Chapter title" placeholder="Chapter title" value={chapterForm.title} onChange={(event) => setChapterForm({ ...chapterForm, title: event.target.value })} required /></div>
              <textarea aria-label="Chapter page image URLs" placeholder="One page image URL per line" value={chapterForm.content} onChange={(event) => setChapterForm({ ...chapterForm, content: event.target.value })} required />
              <Button type="submit" size="sm">{editingChapter ? "Save chapter" : "Add chapter"}</Button>
            </form>}
          </>}
          <div className="premium-callout"><span className="callout-symbol">✳</span><div><strong>Read without limits.</strong><span>Unlock every series with Premium.</span></div><Link href="/pricing" aria-label="View Premium plans">↗</Link></div>
        </aside>
      </section>
      <Toast message={toast} kind={toast.toLowerCase().includes("error") || toast.toLowerCase().includes("premium") || toast.toLowerCase().includes("up to") ? "error" : "success"} />
    </main>
  );
}