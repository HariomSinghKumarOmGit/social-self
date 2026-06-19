import { PostCard } from "./PostCard";
import type { Post } from "../types";

interface Props {
  posts: Post[];
  loading?: boolean;
}

export function ApprovedView({ posts, loading }: Props) {
  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="text-sm text-gray-500">Loading…</div>
      </div>
    );
  }

  if (posts.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
        <p className="text-3xl mb-3">✅</p>
        <p className="text-sm text-gray-500">No approved posts yet.</p>
        <p className="text-xs text-gray-600 mt-1">Swipe right on pending posts to approve them.</p>
      </div>
    );
  }

  return (
    <div className="w-full h-full overflow-y-auto pb-4">
      <div className="grid grid-cols-1 gap-3 p-3 sm:grid-cols-2 lg:grid-cols-3 max-w-screen-xl mx-auto">
        {posts.map((post) => (
          <div key={post.id} className="h-[26rem] sm:h-[30rem]">
            <PostCard post={post} allowScroll={true} showSchedule={true} />
          </div>
        ))}
      </div>
    </div>
  );
}
