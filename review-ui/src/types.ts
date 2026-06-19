export type Platform = "instagram" | "twitter" | "youtube" | string;
export type PostStatus = "pending" | "approved" | "rejected" | "posted";
export type SortKey = "interaction" | "likes" | "newest" | "pending";

export interface Post {
  id: number;
  platform: Platform;
  author: string;
  content: string;
  post_url?: string | null;
  media_url?: string | null;
  likes: number;
  comments: number;
  shares: number;
  saves: number;
  views: number;
  engagement_score: number;
  interaction_score: number;
  created_at: string;
  status: PostStatus;
  scheduled_date?: string | null;
  scheduled_time?: string | null;
  target_account?: string | null;
}

export interface SourceAccounts {
  instagram?: string[];
  twitter?: string[];
  youtube?: string[];
}

export interface ReviewStats {
  total: number;
  total_likes: number;
}
