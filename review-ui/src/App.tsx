import { useCallback, useEffect, useState } from "react";
import { approvePost, fetchApproved, fetchQueue, fetchSourceAccounts, rejectPost, triggerScrape } from "./api";
import { FilterBar } from "./components/FilterBar";
import { SummaryScreen } from "./components/SummaryScreen";
import { SwipeDeck } from "./components/SwipeDeck";
import { ApprovedView } from "./components/ApprovedView";
import type { Post, SourceAccounts } from "./types";

export default function App() {
  const [queue, setQueue] = useState<Post[]>([]);
  const [platform, setPlatform] = useState("");
  const [sort, setSort] = useState("interaction");
  const [stats, setStats] = useState({ total: 0, total_likes: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [scraping, setScraping] = useState(false);
  const [sessionTotal, setSessionTotal] = useState(0);
  const [reviewed, setReviewed] = useState(0);
  const [approvedCount, setApprovedCount] = useState(0);
  const [rejectedCount, setRejectedCount] = useState(0);
  const [byPlatform, setByPlatform] = useState<Record<string, number>>({});

  const [tab, setTab] = useState<"pending" | "approved">("pending");
  const [approvedQueue, setApprovedQueue] = useState<Post[]>([]);
  const [approvedLoading, setApprovedLoading] = useState(false);

  // Load pending queue
  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await fetchQueue({ platform, sort });
      setQueue(data.posts);
      setStats(data.stats);
      setSessionTotal(data.posts.length);
      setReviewed(0);
      setApprovedCount(0);
      setRejectedCount(0);
      setByPlatform({});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [platform, sort]);

  // Load approved posts
  const loadApproved = useCallback(async () => {
    setApprovedLoading(true);
    setError("");
    try {
      const posts = await fetchApproved();
      let filtered = posts;
      if (platform) filtered = filtered.filter((p) => p.platform === platform);
      setApprovedQueue(filtered);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load approved posts");
    } finally {
      setApprovedLoading(false);
    }
  }, [platform]);

  // Load on tab switch
  useEffect(() => {
    if (tab === "pending") {
      load();
    } else {
      loadApproved();
    }
  }, [tab, load, loadApproved]);

  const handleSwipe = async (direction: "left" | "right", post: Post) => {
    setQueue((prev) => prev.filter((p) => p.id !== post.id));
    setReviewed((n) => n + 1);
    const plat = post.platform || "other";
    setByPlatform((m) => ({ ...m, [plat]: (m[plat] || 0) + 1 }));

    try {
      if (direction === "right") {
        await approvePost(post.id);
        setApprovedCount((n) => n + 1);
      } else {
        await rejectPost(post.id);
        setRejectedCount((n) => n + 1);
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
        sort={sort}
        stats={stats}
        onPlatform={(p) => setPlatform(p)}
        onSort={setSort}
        onScrape={handleScrape}
        scraping={scraping}
        tab={tab}
        onTab={setTab}
        approvedCount={approvedQueue.length}
      />

      {error && (
        <p className="bg-red/10 px-4 py-1.5 text-center text-xs text-red">{error}</p>
      )}

      <main className="relative flex flex-1 flex-col justify-center overflow-hidden overscroll-none">
        {tab === "pending" ? (
          <>
            {loading && (
              <p className="text-center text-sm text-gray-500">Loading…</p>
            )}
            {!loading && queue.length === 0 && sessionTotal === 0 && (
              <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
                <p className="text-3xl mb-3">📭</p>
                <p className="text-sm text-gray-500">No pending posts.</p>
                <p className="text-xs text-gray-600 mt-1">Tap Scrape to fetch new content.</p>
              </div>
            )}
            {done && (
              <SummaryScreen
                approved={approvedCount}
                rejected={rejectedCount}
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
