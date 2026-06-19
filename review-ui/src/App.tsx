import { useCallback, useEffect, useState } from "react";
import { approvePost, fetchApproved, fetchQueue, fetchSourceAccounts, rejectPost, startBeast, triggerScrape } from "./api";
import { FilterBar } from "./components/FilterBar";
import { SummaryScreen } from "./components/SummaryScreen";
import { SwipeDeck } from "./components/SwipeDeck";
import { ApprovedView } from "./components/ApprovedView";
import type { Post, SourceAccounts } from "./types";

export default function App() {
  const [queue, setQueue] = useState<Post[]>([]);
  const [accounts, setAccounts] = useState<SourceAccounts>({});
  const [platform, setPlatform] = useState("");
  const [author, setAuthor] = useState("");
  const [sort, setSort] = useState("interaction");
  const [stats, setStats] = useState({ total: 0, total_likes: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [scraping, setScraping] = useState(false);
  const [beastLoading, setBeastLoading] = useState(false);
  const [sessionTotal, setSessionTotal] = useState(0);
  const [reviewed, setReviewed] = useState(0);
  const [approved, setApproved] = useState(0);
  const [rejected, setRejected] = useState(0);
  const [byPlatform, setByPlatform] = useState<Record<string, number>>({});
  
  const [tab, setTab] = useState<"pending" | "approved">("pending");
  const [approvedQueue, setApprovedQueue] = useState<Post[]>([]);
  const [approvedLoading, setApprovedLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [data, acc] = await Promise.all([
        fetchQueue({ platform, author, sort }),
        fetchSourceAccounts(),
      ]);
      setQueue(data.posts);
      setStats(data.stats);
      setAccounts(acc);
      setSessionTotal(data.posts.length);
      setReviewed(0);
      setApproved(0);
      setRejected(0);
      setByPlatform({});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [platform, author, sort]);

  useEffect(() => {
    if (tab === "pending") {
      load();
    } else {
      loadApproved();
    }
  }, [tab, load]);

  const loadApproved = async () => {
    setApprovedLoading(true);
    setError("");
    try {
      const posts = await fetchApproved();
      // Apply same filters (platform, author, sort) if desired, or just show all
      let filtered = posts;
      if (platform) filtered = filtered.filter(p => p.platform === platform);
      if (author) filtered = filtered.filter(p => p.author === author);
      if (sort === "interaction") filtered.sort((a, b) => b.interaction_score - a.interaction_score);
      else if (sort === "likes") filtered.sort((a, b) => b.likes - a.likes);
      else if (sort === "newest") filtered.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      
      setApprovedQueue(filtered);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load approved posts");
    } finally {
      setApprovedLoading(false);
    }
  };

  useEffect(() => {
    if (tab === "approved") {
      loadApproved();
    }
  }, [platform, author, sort]);

  const handleSwipe = async (direction: "left" | "right", post: Post) => {
    setQueue((prev) => prev.filter((p) => p.id !== post.id));
    setReviewed((n) => n + 1);
    const plat = post.platform || "other";
    setByPlatform((m) => ({ ...m, [plat]: (m[plat] || 0) + 1 }));

    try {
      if (direction === "right") {
        await approvePost(post.id);
        setApproved((n) => n + 1);
      } else {
        await rejectPost(post.id);
        setRejected((n) => n + 1);
      }
      setStats((s) => ({
        total: Math.max(0, s.total - 1),
        total_likes: Math.max(0, s.total_likes - post.likes),
      }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
      setQueue((prev) => [post, ...prev]);
      setReviewed((n) => Math.max(0, n - 1));
    }
  };

  const handleStartBeast = async () => {
    setBeastLoading(true);
    try {
      const result = await startBeast();
      if (!result.ok) {
        setError(result.error || "Start Beast failed");
        return;
      }
      if (result.warning) setError(result.warning);
      else setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Start Beast failed");
    } finally {
      setBeastLoading(false);
    }
  };

  const handleScrape = async () => {
    setScraping(true);
    try {
      await triggerScrape();
      setTimeout(load, 8000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Scrape failed");
    } finally {
      setScraping(false);
    }
  };

  const done = !loading && queue.length === 0 && sessionTotal > 0;

  return (
    <div className="flex h-full min-h-[100dvh] flex-col">
      <FilterBar
        platform={platform}
        author={author}
        sort={sort}
        accounts={accounts}
        stats={stats}
        onPlatform={(p) => {
          setPlatform(p);
          setAuthor("");
        }}
        onAuthor={setAuthor}
        onSort={setSort}
        onScrape={handleScrape}
        scraping={scraping}
        onStartBeast={handleStartBeast}
        beastLoading={beastLoading}
        tab={tab}
        onTab={setTab}
      />

      {error && (
        <p className="bg-red/10 px-4 py-2 text-center text-sm text-red">{error}</p>
      )}

      <main className="relative flex flex-1 flex-col justify-center overflow-hidden overscroll-none px-1 sm:px-0">
        {tab === "pending" ? (
          <>
            {loading && (
              <p className="text-center text-gray-500">Loading posts…</p>
            )}
            {!loading && queue.length === 0 && sessionTotal === 0 && (
              <div className="px-6 text-center text-gray-500">
                <p className="text-4xl mb-2">📭</p>
                <p>No pending posts. Run the scraper to fetch content.</p>
              </div>
            )}
            {done && (
              <SummaryScreen
                approved={approved}
                rejected={rejected}
                byPlatform={byPlatform}
                onReload={load}
              />
            )}
            {!loading && queue.length > 0 && (
              <SwipeDeck
                posts={queue}
                onSwipe={handleSwipe}
                reviewedCount={reviewed}
                totalInSession={sessionTotal}
              />
            )}
          </>
        ) : (
          <ApprovedView posts={approvedQueue} loading={approvedLoading} />
        )}
      </main>
    </div>
  );
}
