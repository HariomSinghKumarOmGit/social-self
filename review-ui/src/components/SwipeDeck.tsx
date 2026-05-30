import { useRef, useState } from "react";
import { animate, motion, useMotionValue, useTransform } from "framer-motion";
import type { Post } from "../types";
import { PostCard } from "./PostCard";

const SWIPE_THRESHOLD = 72;

interface Props {
  posts: Post[];
  onSwipe: (direction: "left" | "right", post: Post) => void;
  reviewedCount: number;
  totalInSession: number;
}

export function SwipeDeck({ posts, onSwipe, reviewedCount, totalInSession }: Props) {
  const [exitDir, setExitDir] = useState<"left" | "right" | null>(null);
  const stack = posts.slice(0, 3);

  if (!stack.length) return null;

  return (
    <div className="swipe-deck relative mx-auto w-full max-w-md px-2 sm:px-4">
      <p className="mb-2 text-center text-sm text-gray-400 sm:mb-3">
        {reviewedCount} / {totalInSession} reviewed · swipe or tap ✓ ✗
      </p>
      <div className="relative h-[min(calc(100dvh-13rem),560px)] w-full">
        {stack.map((post, index) => {
          const isTop = index === 0;
          return (
            <SwipeCard
              key={post.id}
              post={post}
              index={index}
              isTop={isTop}
              exitDir={isTop ? exitDir : null}
              onSwipe={(dir) => {
                setExitDir(dir);
                setTimeout(() => {
                  onSwipe(dir, post);
                  setExitDir(null);
                }, 280);
              }}
            />
          );
        })}
      </div>
    </div>
  );
}

function SwipeCard({
  post,
  index,
  isTop,
  exitDir,
  onSwipe,
}: {
  post: Post;
  index: number;
  isTop: boolean;
  exitDir: "left" | "right" | null;
  onSwipe: (dir: "left" | "right") => void;
}) {
  const x = useMotionValue(0);
  const rotate = useTransform(x, [-220, 0, 220], [-14, 0, 14]);
  const approveOpacity = useTransform(x, [0, 60, 120], [0, 0.55, 1]);
  const rejectOpacity = useTransform(x, [-120, -60, 0], [1, 0.55, 0]);

  const scale = 1 - index * 0.05;
  const y = index * 8;
  const opacity = 1 - index * 0.12;

  const origin = useRef<{ x: number; y: number } | null>(null);
  const dragging = useRef(false);

  const flyOff = exitDir === "right" ? 520 : exitDir === "left" ? -520 : 0;

  const finishSwipe = (offset: number) => {
    if (offset > SWIPE_THRESHOLD) {
      onSwipe("right");
      return;
    }
    if (offset < -SWIPE_THRESHOLD) {
      onSwipe("left");
      return;
    }
    animate(x, 0, { type: "spring", stiffness: 420, damping: 32 });
  };

  const onPointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!isTop || exitDir) return;
    origin.current = { x: event.clientX, y: event.clientY };
    dragging.current = false;
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const onPointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!isTop || !origin.current || exitDir) return;

    const dx = event.clientX - origin.current.x;
    const dy = event.clientY - origin.current.y;

    if (!dragging.current) {
      if (Math.abs(dx) < 6 && Math.abs(dy) < 6) return;
      if (Math.abs(dx) <= Math.abs(dy)) return;
      dragging.current = true;
    }

    if (dragging.current) {
      event.preventDefault();
      x.set(dx);
    }
  };

  const onPointerUp = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!isTop) return;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    if (!origin.current) return;
    origin.current = null;
    finishSwipe(x.get());
    dragging.current = false;
  };

  const onPointerCancel = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!isTop) return;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    origin.current = null;
    dragging.current = false;
    animate(x, 0, { type: "spring", stiffness: 420, damping: 32 });
  };

  if (exitDir && isTop) {
    return (
      <motion.div
        className="swipe-card absolute inset-0"
        style={{ scale, y, zIndex: 30 - index, opacity }}
        animate={{ x: flyOff, rotate: exitDir === "right" ? 18 : -18, opacity: 0 }}
        transition={{ duration: 0.28 }}
      >
        <PostCard post={post} overlay={exitDir === "right" ? "approve" : "reject"} />
      </motion.div>
    );
  }

  return (
    <motion.div
      className={`swipe-card absolute inset-0 ${isTop ? "cursor-grab active:cursor-grabbing" : ""}`}
      style={{
        x: isTop ? x : 0,
        rotate: isTop ? rotate : 0,
        scale,
        y,
        zIndex: 30 - index,
        opacity,
        touchAction: isTop ? "none" : "auto",
      }}
      onPointerDown={isTop ? onPointerDown : undefined}
      onPointerMove={isTop ? onPointerMove : undefined}
      onPointerUp={isTop ? onPointerUp : undefined}
      onPointerCancel={isTop ? onPointerCancel : undefined}
    >
      <div className="relative h-full w-full select-none">
        <PostCard post={post} allowScroll={!isTop} />
        {isTop && (
          <>
            <motion.div
              className="pointer-events-none absolute inset-0 flex items-center justify-center rounded-2xl bg-green/30 text-5xl sm:text-6xl"
              style={{ opacity: approveOpacity }}
            >
              ✓
            </motion.div>
            <motion.div
              className="pointer-events-none absolute inset-0 flex items-center justify-center rounded-2xl bg-red/30 text-5xl sm:text-6xl"
              style={{ opacity: rejectOpacity }}
            >
              ✗
            </motion.div>
          </>
        )}
      </div>
    </motion.div>
  );
}
