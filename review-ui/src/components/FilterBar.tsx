import type { SourceAccounts } from "../types";

interface Props {
  platform: string;
  author: string;
  sort: string;
  accounts: SourceAccounts;
  stats: { total: number; total_likes: number };
  onPlatform: (p: string) => void;
  onAuthor: (a: string) => void;
  onSort: (s: string) => void;
  onScrape: () => void;
  scraping: boolean;
  onStartBeast: () => void;
  beastLoading: boolean;
}

export function FilterBar({
  platform,
  author,
  sort,
  accounts,
  stats,
  onPlatform,
  onAuthor,
  onSort,
  onScrape,
  scraping,
  onStartBeast,
  beastLoading,
}: Props) {
  const authors = platform ? accounts[platform as keyof SourceAccounts] || [] : [];

  const platforms = [
    { id: "", label: "All" },
    { id: "instagram", label: "📸 Insta" },
    { id: "twitter", label: "𝕏 Twitter" },
    { id: "youtube", label: "▶ YouTube" },
  ];

  return (
    <header className="shrink-0 border-b border-border bg-surface/95 px-3 py-3 backdrop-blur md:px-6">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <a href="/" className="text-sm text-gray-400 hover:text-white">
            ← Calendar
          </a>
          <h1 className="text-lg font-bold">
            Review <span className="text-accent">Stack</span>
          </h1>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onStartBeast}
            disabled={beastLoading}
            className="rounded-full px-3 py-1.5 text-xs font-extrabold uppercase tracking-wide text-white disabled:opacity-60"
            style={{
              background: "linear-gradient(135deg, #ff6b35, #f72585 55%, #7209b7)",
            }}
          >
            {beastLoading ? "Starting…" : "Start Beast"}
          </button>
          <button
            type="button"
            onClick={onScrape}
            disabled={scraping}
            className="rounded-full border border-green/40 bg-green/10 px-3 py-1.5 text-xs font-semibold text-green disabled:opacity-50"
          >
            {scraping ? "Scraping…" : "🔄 Scrape"}
          </button>
        </div>
      </div>

      <div className="mb-2 flex flex-wrap gap-1.5">
        {platforms.map((p) => (
          <button
            key={p.id || "all"}
            type="button"
            onClick={() => onPlatform(p.id)}
            className={`rounded-full px-3 py-1.5 text-xs font-medium ${
              platform === p.id
                ? "bg-accent/20 text-accent ring-1 ring-accent"
                : "bg-card text-gray-400 ring-1 ring-border"
            }`}
          >
            {p.label}
          </button>
        ))}
        <select
          value={sort}
          onChange={(e) => onSort(e.target.value)}
          className="ml-auto rounded-full border border-border bg-card px-3 py-1.5 text-xs text-gray-300"
        >
          <option value="interaction">Most interactions</option>
          <option value="likes">Most likes</option>
          <option value="newest">Most recent</option>
        </select>
      </div>

      {authors.length > 0 && (
        <div className="mb-2 flex gap-1.5 overflow-x-auto pb-1 scrollbar-hide">
          <button
            type="button"
            onClick={() => onAuthor("")}
            className={`shrink-0 rounded-full px-3 py-1 text-xs ${
              !author ? "bg-white/10 text-white" : "bg-card text-gray-500"
            }`}
          >
            All accounts
          </button>
          {authors.map((a) => (
            <button
              key={a}
              type="button"
              onClick={() => onAuthor(a)}
              className={`shrink-0 rounded-full px-3 py-1 text-xs ${
                author === a ? "bg-sky-500/20 text-sky-300" : "bg-card text-gray-500"
              }`}
            >
              @{a}
            </button>
          ))}
        </div>
      )}

      <p className="text-xs text-gray-500">
        <strong className="text-gray-300">{stats.total}</strong> posts ·{" "}
        <strong className="text-gray-300">{stats.total_likes.toLocaleString()}</strong> total likes
      </p>
    </header>
  );
}
