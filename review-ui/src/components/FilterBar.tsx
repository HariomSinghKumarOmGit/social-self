import type { SourceAccounts } from "../types";

interface Props {
  platform: string;
  sort: string;
  stats: { total: number; total_likes: number };
  onPlatform: (p: string) => void;
  onSort: (s: string) => void;
  onScrape: () => void;
  scraping: boolean;
  tab: "pending" | "approved";
  onTab: (tab: "pending" | "approved") => void;
  approvedCount: number;
}

export function FilterBar({
  platform,
  sort,
  stats,
  onPlatform,
  onSort,
  onScrape,
  scraping,
  tab,
  onTab,
  approvedCount,
}: Props) {
  const platforms = [
    { id: "", label: "All" },
    { id: "instagram", label: "📸" },
    { id: "twitter", label: "𝕏" },
    { id: "youtube", label: "▶" },
  ];

  return (
    <header className="sticky top-0 z-40 shrink-0 border-b border-border bg-surface/95 backdrop-blur">
      {/* Top row: title + scrape */}
      <div className="flex items-center justify-between px-3 py-2 sm:px-4">
        <div className="flex items-center gap-2 min-w-0">
          <a href="/" className="text-gray-500 hover:text-white text-xs">←</a>
          <h1 className="text-sm font-bold sm:text-base truncate">
            Review
          </h1>
        </div>
        <button
          type="button"
          onClick={onScrape}
          disabled={scraping}
          className="shrink-0 rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-[11px] font-medium text-accent disabled:opacity-50"
        >
          {scraping ? "Scraping…" : "↻ Scrape"}
        </button>
      </div>

      {/* Tabs + filters row */}
      <div className="flex items-center gap-2 px-3 pb-2 sm:px-4 overflow-x-auto scrollbar-hide">
        {/* Tabs */}
        <div className="flex shrink-0 rounded-lg bg-black/30 p-0.5">
          <button
            type="button"
            onClick={() => onTab("pending")}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-all ${
              tab === "pending"
                ? "bg-card text-white shadow-sm"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            Pending
            {tab === "pending" && stats.total > 0 && (
              <span className="ml-1 text-accent">{stats.total}</span>
            )}
          </button>
          <button
            type="button"
            onClick={() => onTab("approved")}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-all ${
              tab === "approved"
                ? "bg-card text-white shadow-sm"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            Approved
            {approvedCount > 0 && (
              <span className={`ml-1 ${tab === "approved" ? "text-green" : "text-gray-600"}`}>
                {approvedCount}
              </span>
            )}
          </button>
        </div>

        {/* Divider */}
        <div className="h-4 w-px bg-border shrink-0" />

        {/* Platform filters */}
        {platforms.map((p) => (
          <button
            key={p.id || "all"}
            type="button"
            onClick={() => onPlatform(p.id)}
            className={`shrink-0 rounded-md px-2 py-1 text-xs transition-all ${
              platform === p.id
                ? "bg-accent/15 text-accent"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            {p.label}
          </button>
        ))}

        {/* Sort */}
        <select
          value={sort}
          onChange={(e) => onSort(e.target.value)}
          className="ml-auto shrink-0 rounded-md border-0 bg-transparent px-1 py-1 text-[11px] text-gray-500 outline-none"
        >
          <option value="interaction">Top</option>
          <option value="likes">Likes</option>
          <option value="newest">New</option>
        </select>
      </div>
    </header>
  );
}
