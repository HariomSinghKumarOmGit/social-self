import type { Post } from "../types";
import { fmtDate, fmtNum, platformLabel, postLink } from "../utils";

const PLATFORM_ICON: Record<string, string> = {
  instagram: "📸",
  twitter: "𝕏",
  youtube: "▶",
};

const ACCENT: Record<string, string> = {
  instagram: "from-pink-600/30",
  twitter: "from-sky-600/30",
  youtube: "from-red-600/30",
};

interface Props {
  post: Post;
  overlay?: "approve" | "reject" | null;
  /** Top swipe card should not scroll — inner scroll steals touch on mobile. */
  allowScroll?: boolean;
}

export function PostCard({ post, overlay, allowScroll = true }: Props) {
  const p = (post.platform || "").toLowerCase();
  const icon = PLATFORM_ICON[p] || "📝";
  const gradient = ACCENT[p] || "from-accent/20";

  return (
    <div className="relative flex h-full w-full flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-2xl sm:max-w-md">
      <div className={`bg-gradient-to-b ${gradient} to-transparent px-4 pb-2 pt-4`}>
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-black/30 text-xl">
            {icon}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate font-semibold">@{post.author}</div>
            <div className="text-xs text-gray-400">
              {platformLabel(p)} · {fmtDate(post.created_at)}
            </div>
          </div>
          <div className="rounded-lg bg-black/40 px-2 py-1 text-xs font-bold text-green">
            {post.interaction_score.toFixed(1)}
          </div>
        </div>
      </div>

      <div
        className={`flex-1 px-4 py-3 ${
          allowScroll ? "overflow-y-auto overscroll-contain" : "overflow-hidden"
        }`}
      >
        <p
          className={`whitespace-pre-wrap text-[15px] leading-relaxed text-gray-100 ${
            allowScroll ? "" : "line-clamp-[12] sm:line-clamp-[14]"
          }`}
        >
          {post.content}
        </p>
        {post.media_url ? (
          <img
            src={post.media_url}
            alt=""
            draggable={false}
            className={`mt-3 w-full rounded-xl border border-border object-cover ${
              allowScroll ? "max-h-56" : "max-h-40 sm:max-h-48"
            }`}
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        ) : null}
        <a
          href={postLink(post)}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 block truncate text-xs text-accent hover:underline"
          draggable={false}
        >
          Open original post →
        </a>
      </div>

      <div className="grid grid-cols-3 gap-1 border-t border-border bg-black/20 px-2 py-2 text-center text-[9px] uppercase tracking-wide text-gray-500 sm:grid-cols-5 sm:py-3 sm:text-[10px]">
        <Stat label="Likes" value={fmtNum(post.likes)} icon="❤️" />
        <Stat label="Comments" value={fmtNum(post.comments)} icon="💬" />
        <Stat label="Shares" value={fmtNum(post.shares)} icon="🔁" />
        <Stat label="Saves" value={fmtNum(post.saves)} icon="🔖" />
        <Stat label="Views" value={fmtNum(post.views)} icon="👁" />
      </div>

      <div className="absolute right-3 top-3 rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] font-bold uppercase text-amber-300">
        {post.status}
      </div>

      {overlay === "approve" && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center rounded-2xl bg-green/25">
          <span className="text-6xl">✓</span>
        </div>
      )}
      {overlay === "reject" && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center rounded-2xl bg-red/25">
          <span className="text-6xl">✗</span>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, icon }: { label: string; value: string; icon: string }) {
  return (
    <div>
      <div className="text-sm font-bold text-white">{value}</div>
      <div className="mt-0.5">{icon}</div>
      <div>{label}</div>
    </div>
  );
}
