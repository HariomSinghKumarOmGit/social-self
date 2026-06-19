interface Props {
  onReject: () => void;
  onApprove: () => void;
  disabled?: boolean;
}

export function SwipeActions({ onReject, onApprove, disabled }: Props) {
  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 border-t border-border bg-surface/95 backdrop-blur safe-pb">
      <div className="mx-auto flex max-w-md items-center justify-center gap-8 px-4 py-3">
        <button
          type="button"
          aria-label="Reject"
          disabled={disabled}
          onClick={onReject}
          className="flex h-12 w-12 items-center justify-center rounded-full border border-red/40 bg-red/10 text-2xl text-red shadow-lg shadow-red/10 transition active:scale-90 disabled:opacity-30 sm:h-14 sm:w-14"
        >
          ✕
        </button>

        <button
          type="button"
          aria-label="Approve"
          disabled={disabled}
          onClick={onApprove}
          className="flex h-14 w-14 items-center justify-center rounded-full border border-green/40 bg-green/10 text-3xl text-green shadow-lg shadow-green/10 transition active:scale-90 disabled:opacity-30 sm:h-16 sm:w-16"
        >
          ✓
        </button>
      </div>
    </div>
  );
}
