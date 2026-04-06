"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function UpgradePage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/pricing");
  }, [router]);
  return null;
}
