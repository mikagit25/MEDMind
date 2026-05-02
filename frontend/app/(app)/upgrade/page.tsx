"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store";
import { api } from "@/lib/api";

const PLANS = [
  {
    tier: "student",
    name: "Student",
    price: "$15/mo",
    priceId: "price_student_monthly",
    description: "All 80+ medical modules, 50 AI questions/day",
    color: "border-blue bg-blue-light",
    cta: "Upgrade to Student",
  },
  {
    tier: "pro",
    name: "Pro",
    price: "$40/mo",
    priceId: "price_pro_monthly",
    description: "Unlimited AI, drug database, PubMed, vet content",
    color: "border-red bg-red-light",
    cta: "Upgrade to Pro",
    highlight: true,
  },
  {
    tier: "lifetime",
    name: "Lifetime",
    price: "$299 once",
    priceId: "price_lifetime",
    description: "Everything in Pro, forever, all future content",
    color: "border-amber bg-amber-light",
    cta: "Get Lifetime Access",
  },
];

export default function UpgradePage() {
  const { user } = useAuthStore();
  const router = useRouter();

  // If already on pro or higher, redirect to settings
  useEffect(() => {
    if (user?.subscription_tier && ["pro", "clinic", "lifetime"].includes(user.subscription_tier)) {
      router.replace("/settings");
    }
  }, [user, router]);

  const [error, setError] = useState("");
  const currentTier = user?.subscription_tier || "free";

  const handleUpgrade = async (tier: string) => {
    try {
      const res = await api.post("/payments/create-checkout", {
        tier,
        success_url: `${window.location.origin}/dashboard?upgraded=1`,
        cancel_url: `${window.location.origin}/upgrade`,
      });
      window.location.href = res.data.url;
    } catch {
      setError("Could not start checkout. Please try again.");
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="font-syne font-bold text-2xl text-ink mb-2">Upgrade your plan</h1>
        <p className="text-ink-2">
          You're on the <span className="font-syne font-semibold capitalize">{currentTier}</span> plan.
          Unlock more content and AI capabilities.
        </p>
      </div>

      <div className="space-y-4">
        {PLANS.filter(p => {
          if (currentTier === "student") return p.tier !== "student";
          return true;
        }).map((plan) => (
          <div
            key={plan.tier}
            className={`rounded-xl border-2 p-6 flex items-center justify-between gap-6 ${plan.color}`}
          >
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-1">
                <span className="font-syne font-bold text-xl text-ink">{plan.name}</span>
                {plan.highlight && (
                  <span className="bg-red text-white text-xs font-syne font-bold px-2 py-0.5 rounded-full">
                    Most Popular
                  </span>
                )}
              </div>
              <p className="text-ink-2 text-sm">{plan.description}</p>
            </div>
            <div className="text-right flex-shrink-0">
              <div className="font-syne font-bold text-xl text-ink mb-2">{plan.price}</div>
              <button
                onClick={() => handleUpgrade(plan.tier)}
                className="btn-primary text-sm px-5 py-2 whitespace-nowrap"
              >
                {plan.cta}
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 text-center">
        <a href="/pricing" className="text-sm text-ink-2 hover:text-ink underline">
          Compare all plans in detail →
        </a>
      </div>
    </div>
  );
}
