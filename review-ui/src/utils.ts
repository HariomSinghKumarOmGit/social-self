import type { Post } from "./types";

export function interactionScore(p: Pick<Post, "likes" | "comments" | "shares" | "saves" | "views">): number {
  return (
    Number(p.likes || 0) +
    Number(p.comments || 0) * 3 +
    Number(p.shares || 0) * 2 +
    Number(p.saves || 0) * 2 +
    Number(p.views || 0) * 0.01
  );
}

export function fmtNum(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export function fmtDate(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso.slice(0, 16).replace("T", " ");
  return d.toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function platformLabel(p: string): string {
  if (p === "twitter") return "X / Twitter";
  if (p === "instagram") return "Instagram";
  if (p === "youtube") return "YouTube";
  return p;
}

export function postLink(post: Post): string {
  if (post.post_url) return post.post_url;
  const a = post.author || "";
  if (post.platform === "twitter") return `https://x.com/${a}`;
  if (post.platform === "instagram") return `https://www.instagram.com/${a}/`;
  if (post.platform === "youtube") return `https://www.youtube.com/@${a}`;
  return "#";
}

export function sortPosts(posts: Post[], sort: string): Post[] {
  const list = [...posts];
  if (sort === "likes") {
    list.sort((a, b) => b.likes - a.likes);
  } else if (sort === "newest") {
    list.sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""));
  } else if (sort === "pending") {
    list.sort((a, b) => (a.status === "pending" ? -1 : 1));
  } else {
    list.sort((a, b) => b.interaction_score - a.interaction_score);
  }
  return list;
}

export function filterPosts(
  posts: Post[],
  platform: string,
  author: string,
  query: string
): Post[] {
  let list = posts;
  if (platform) {
    list = list.filter((p) => (p.platform || "").toLowerCase() === platform);
  }
  if (author) {
    list = list.filter((p) => (p.author || "").toLowerCase() === author.toLowerCase());
  }
  if (query.trim()) {
    const q = query.toLowerCase();
    list = list.filter(
      (p) =>
        (p.content || "").toLowerCase().includes(q) ||
        (p.author || "").toLowerCase().includes(q)
    );
  }
  return list;
}
