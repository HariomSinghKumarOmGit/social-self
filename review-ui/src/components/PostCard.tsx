import type { Post } from "../types";
import { fmtDate, fmtNum, platformLabel, postLink } from "../utils";

const PLATFORM_ICON: Record<string, string> = {
  instagram: "📸",
  twitter: "𝕏",
  youtube: "▶",
};

interface Props {
  post: Post;
  overlay?: "approve" | "reject" | null;
  allowScroll?: boolean;
  showSchedule?: boolean;
}

export function PostCard({ post, overlay, allowScroll = true, showSchedule }: Props) {
  const p = (post.platform || "").toLowerCase();
  const icon = PLATFORM_ICON[p] || "📝";
  const link = postLink(post);
  const score = (post.interaction_score ?? 0).toFixed(0);

  return (
    <div className="relative flex h-full w-full flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-xl">
      {/* Header */}
      <div className="flex items-center gap-2.5 px-3 py-2.5 sm:px-4 sm:py-3">
        <span className="text-lg">{icon}</span>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold">@{post.author}</div>
          <div className="text-[11px] text-gray-500">
            {platformLabel(p)} · {fmtDate(post.created_at)}
          </div>
        </div>
        <div className="shrink-0 rounded-md bg-green/10 px-1.5 py-0.5 text-[11px] font-bold text-green">
          {score}
        </div>
      </div>

      {/* Content */}
      <div
        className={`flex-1 px-3 py-2 sm:px-4 ${
          allowScroll ? "overflow-y-auto overscroll-contain" : "overflow-hidden"
        }`}
      >
        <p
          className={`whitespace-pre-wrap text-[13px] leading-relaxed text-gray-200 sm:text-sm ${
            allowScroll ? "" : "line-clamp-[10] sm:line-clamp-[12]"
          }`}
        >
          {post.content}
        </p>
        {post.media_url ? (
          <img
            src={post.media_url}
            alt=""
            draggable={false}
            className={`mt-2 w-full rounded-lg border border-border object-cover ${
              allowScroll ? "max-h-48" : "max-h-32 sm:max-h-40"
            }`}
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        ) : null}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-5 gap-1 border-t border-border px-2 py-1.5 text-center text-[9px] text-gray-500">
        <Stat value={fmtNum(post.likes)} icon="❤️" />
        <Stat value={fmtNum(post.comments)} icon="💬" />
        <Stat value={fmtNum(post.shares)} icon="🔁" />
        <Stat value={fmtNum(post.saves)} icon="🔖" />
        <Stat value={fmtNum(post.views)} icon="👁" />
      </div>

      {/* Link bar */}
      {link && link !== "#" && (
        <a
          href={link}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 border-t border-border px-3 py-2 text-[11px] text-accent hover:bg-accent/5 transition-colors sm:px-4"
          draggable={false}
        >
          <span>🔗</span>
          <span className="truncate flex-1">{link}</span>
          <span className="shrink-0">→</span>
        </a>
      )}

      {/* Schedule info */}
      {showSchedule && post.scheduled_date && (
        <div className="border-t border-border px-3 py-1.5 text-[11px] text-gray-500 sm:px-4">
          📅 {post.scheduled_date}
          {post.scheduled_time && <span className="ml-1">at {post.scheduled_time}</span>}
          {post.target_account && (
            <span className="ml-2 text-accent">→ @{post.target_account}</span>
          )}
        </div>
      )}

      {/* Overlays */}
      {overlay === "approve" && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center rounded-2xl bg-green/20">
          <span className="text-5xl">✓</span>
        </div>
      )}
      {overlay === "reject" && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center rounded-2xl bg-red/20">
          <span className="text-5xl">✗</span>
        </div>
      )}
    </div>
  );
}

function Stat({ value, icon }: { value: string; icon: string }) {
  return (
    <div>
      <div className="text-xs font-semibold text-gray-300">{value}</div>
      <div className="mt-0.5">{icon}</div>
    </div>
  );
}
