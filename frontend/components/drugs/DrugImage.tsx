"use client";
import { useState } from "react";

export function DrugImage({ src, alt }: { src: string; alt: string }) {
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <span className="text-4xl">💊</span>
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      className="w-full h-full object-contain p-1"
      onError={() => setFailed(true)}
    />
  );
}
