import type { Post } from "../types";

interface Props {
  approved: number;
  rejected: number;
  byPlatform: Record<string, number>;
  onReload: () => void;
}

export function SummaryScreen({ approved, rejected, byPlatform, onReload }: Props) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
      <div className="text-5xl mb-4">🎉</div>
      <h2 className="text-2xl font-bold">All caught up</h2>
      <p className="mt-2 text-gray-400">You reviewed every post in this queue.</p>
      <div className="mt-8 grid w-full max-w-sm grid-cols-2 gap-4">
        <div className="rounded-xl border border-green/30 bg-green/10 p-4">
          <div className="text-3xl font-bold text-green">{approved}</div>
          <div className="text-sm text-gray-400">Approved</div>
        </div>
        <div className="rounded-xl border border-red/30 bg-red/10 p-4">
          <div className="text-3xl font-bold text-red">{rejected}</div>
          <div className="text-sm text-gray-400">Rejected</div>
        </div>
      </div>
      {Object.keys(byPlatform).length > 0 && (
        <ul className="mt-6 w-full max-w-sm text-left text-sm text-gray-400">
          {Object.entries(byPlatform).map(([plat, n]) => (
            <li key={plat} className="flex justify-between border-b border-border py-2">
              <span className="capitalize">{plat}</span>
              <span>{n}</span>
            </li>
          ))}
        </ul>
      )}
      <button
        type="button"
        onClick={onReload}
        className="mt-8 rounded-full bg-accent px-6 py-2.5 text-sm font-semibold text-white"
      >
        Reload queue
      </button>
    </div>
  );
}

export type ReviewedPost = Post & { decision: "approved" | "rejected" };
