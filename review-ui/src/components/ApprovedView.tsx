import { PostCard } from "./PostCard";
import type { Post } from "../types";

interface Props {
  posts: Post[];
  loading?: boolean;
}

export function ApprovedView({ posts, loading }: Props) {
  if (loading) {
    return <p className="text-center text-gray-500 mt-10">Loading approved posts…</p>;
  }

  if (posts.length === 0) {
    return (
      <div className="px-6 text-center text-gray-500 mt-20 flex flex-col items-center">
        <p className="text-4xl mb-4">✅</p>
        <p>No approved posts found.</p>
      </div>
    );
  }

  return (
    <div className="w-full h-full overflow-y-auto pb-20">
      <div className="grid grid-cols-1 gap-6 p-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 max-w-screen-2xl mx-auto">
        {posts.map((post) => (
          <div key={post.id} className="h-[28rem] sm:h-[32rem]">
            <PostCard post={post} allowScroll={true} />
          </div>
        ))}
      </div>
    </div>
  );
}
