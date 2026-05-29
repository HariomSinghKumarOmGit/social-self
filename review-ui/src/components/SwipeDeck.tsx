import { useState } from "react";
import { motion, useMotionValue, useTransform, animate, PanInfo } from "framer-motion";
import type { Post } from "../types";
import { PostCard } from "./PostCard";

const SWIPE_THRESHOLD = 120;

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
    <div className="relative mx-auto h-[min(72vh,640px)] w-full max-w-md px-4">
      <p className="mb-3 text-center text-sm text-gray-400">
        {reviewedCount} / {totalInSession} reviewed
      </p>
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
  const rotate = useTransform(x, [-200, 0, 200], [-18, 0, 18]);
  const approveOpacity = useTransform(x, [0, 80, 160], [0, 0.5, 1]);
  const rejectOpacity = useTransform(x, [-160, -80, 0], [1, 0.5, 0]);

  const scale = 1 - index * 0.05;
  const y = index * 10;
  const opacity = 1 - index * 0.12;

  const flyOff = exitDir === "right" ? 500 : exitDir === "left" ? -500 : 0;

  if (exitDir && isTop) {
    return (
      <motion.div
        className="absolute inset-x-4 top-8"
        style={{ scale, y, zIndex: 30 - index, opacity }}
        animate={{ x: flyOff, rotate: exitDir === "right" ? 20 : -20, opacity: 0 }}
        transition={{ duration: 0.28 }}
      >
        <PostCard post={post} overlay={exitDir === "right" ? "approve" : "reject"} />
      </motion.div>
    );
  }

  return (
    <motion.div
      className="absolute inset-x-4 top-8 touch-none"
      style={{
        x: isTop ? x : 0,
        rotate: isTop ? rotate : 0,
        scale,
        y,
        zIndex: 30 - index,
        opacity,
      }}
      drag={isTop ? "x" : false}
      dragElastic={0.9}
      dragConstraints={{ left: 0, right: 0 }}
      onDragEnd={(_e, info: PanInfo) => {
        if (info.offset.x > SWIPE_THRESHOLD) {
          onSwipe("right");
        } else if (info.offset.x < -SWIPE_THRESHOLD) {
          onSwipe("left");
        } else {
          animate(x, 0, { type: "spring", stiffness: 400, damping: 30 });
        }
      }}
    >
      <div className="relative h-full w-full">
        <PostCard post={post} />
        <motion.div
          className="pointer-events-none absolute inset-0 rounded-2xl bg-green/30 flex items-center justify-center text-6xl"
          style={{ opacity: approveOpacity }}
        >
          ✓
        </motion.div>
        <motion.div
          className="pointer-events-none absolute inset-0 rounded-2xl bg-red/30 flex items-center justify-center text-6xl"
          style={{ opacity: rejectOpacity }}
        >
          ✗
        </motion.div>
      </div>
    </motion.div>
  );
}
