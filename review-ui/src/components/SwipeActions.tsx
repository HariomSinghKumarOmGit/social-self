interface Props {
  onReject: () => void;
  onApprove: () => void;
  disabled?: boolean;
}

export function SwipeActions({ onReject, onApprove, disabled }: Props) {
  return (
    <div className="swipe-actions fixed bottom-0 left-0 right-0 z-50 border-t border-border bg-[#0f1118]/95 px-4 py-3 backdrop-blur safe-pb sm:py-4">
      <div className="mx-auto flex max-w-md items-center justify-center gap-10 sm:gap-14">
        <button
          type="button"
          aria-label="Reject post"
          disabled={disabled}
          onClick={onReject}
          className="group flex flex-col items-center gap-1 disabled:opacity-40"
        >
          <span className="flex h-14 w-14 items-center justify-center rounded-full border-2 border-red/50 bg-red/20 text-3xl font-bold text-red shadow-lg shadow-red/25 transition active:scale-95 sm:h-16 sm:w-16">
            ✕
          </span>
          <span className="text-[11px] font-semibold uppercase tracking-wide text-red">Reject</span>
        </button>

        <button
          type="button"
          aria-label="Approve post"
          disabled={disabled}
          onClick={onApprove}
          className="group flex flex-col items-center gap-1 disabled:opacity-40"
        >
          <span className="flex h-16 w-16 items-center justify-center rounded-full border-2 border-green/50 bg-green/20 text-4xl font-bold text-green shadow-lg shadow-green/25 transition active:scale-95 sm:h-[4.5rem] sm:w-[4.5rem]">
            ✓
          </span>
          <span className="text-[11px] font-semibold uppercase tracking-wide text-green">Approve</span>
        </button>
      </div>
    </div>
  );
}
