"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type RegionalPricing = {
  tier: string;
  discount_pct: number;
  prices: Record<string, number>;
};

export function RegionalPriceBadge({ plan = "gulf_bundle" }: { plan?: string }) {
  const [data, setData] = useState<RegionalPricing | null>(null);

  useEffect(() => {
    api.get("/pricing/regional").then(res => {
      if (res.data?.discount_pct > 0) setData(res.data);
    }).catch(() => {});
  }, []);

  if (!data) return null;
  const price = data.prices[plan];
  if (!price) return null;

  return (
    <div className="inline-flex items-center gap-2 bg-green/10 border border-green/20 rounded-lg px-3 py-1.5 text-xs font-syne">
      <span className="text-green font-bold">🌍 Regional price: ${price.toFixed(0)}/mo</span>
      <span className="text-ink-3">({data.discount_pct}% off)</span>
    </div>
  );
}
