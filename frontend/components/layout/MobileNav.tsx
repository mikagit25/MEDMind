"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useEffect, useRef } from "react";
import { useAuthStore, useUIStore } from "@/lib/store";
import { NotificationBell } from "@/components/ui/NotificationBell";
import { clsx } from "clsx";
import { useT } from "@/lib/i18n";

// ── Bottom tabs — 5 key destinations ──────────────────────────────────────────
const BOTTOM_TABS = [
  { icon: "🏠", labelKey: "nav.items.dashboard", href: "/dashboard" },
  { icon: "📚", labelKey: "nav.items.modules",   href: "/modules"   },
  { icon: "🤖", labelKey: "nav.items.ai_tutor",  href: "/ai-tutor"  },
  { icon: "🩻", labelKey: "nav.items.imaging",   href: "/imaging"   },
  { icon: "💊", labelKey: "nav.items.drugs",      href: "/drugs"     },
] as const;

// ── Drawer nav sections (mirrors Sidebar) ─────────────────────────────────────
function DrawerNav({ onClose }: { onClose: () => void }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthStore();
  const { darkMode, toggleDarkMode } = useUIStore();
  const [searchQ, setSearchQ] = useState("");
  const t = useT();

  const NAV_SECTIONS = [
    {
      label: t("nav.sections.learning"),
      items: [
        { icon: "🏠", label: t("nav.items.dashboard"),  href: "/dashboard"     },
        { icon: "📚", label: t("nav.items.modules"),    href: "/modules"       },
        { icon: "🎓", label: t("nav.items.my_courses"), href: "/my-courses"    },
        { icon: "🤖", label: t("nav.items.ai_tutor"),   href: "/ai-tutor"      },
        { icon: "🃏", label: t("nav.items.flashcards"), href: "/flashcards"    },
        { icon: "📇", label: t("nav.items.my_cards"),   href: "/my-flashcards" },
        { icon: "📝", label: t("nav.items.quiz"),        href: "/quiz"          },
        { icon: "🩺", label: t("nav.items.cases"),      href: "/cases"         },
        { icon: "🏥", label: t("nav.items.simulation"), href: "/simulation"    },
      ],
    },
    {
      label: t("nav.sections.visual_medicine"),
      items: [
        { icon: "🩻", label: t("nav.items.imaging"),    href: "/imaging"  },
        { icon: "🧊", label: t("nav.items.anatomy_3d"), href: "/anatomy"  },
      ],
    },
    {
      label: t("nav.sections.tools"),
      items: [
        { icon: "📰", label: t("nav.items.articles"),    href: "/knowledge"       },
        { icon: "💊", label: t("nav.items.drugs"),       href: "/drugs"           },
        { icon: "🐾", label: t("nav.items.veterinary"),  href: "/veterinary"      },
        { icon: "📈", label: t("nav.items.progress"),    href: "/progress"        },
        { icon: "🏆", label: t("nav.items.leaderboard"), href: "/leaderboard"     },
        { icon: "🎯", label: t("nav.items.for_you"),     href: "/recommendations" },
      ],
    },
    {
      label: t("nav.sections.account"),
      items: [
        { icon: "🏅", label: t("nav.items.achievements"),  href: "/achievements" },
        { icon: "🔖", label: t("nav.items.bookmarks"),     href: "/bookmarks"    },
        { icon: "🔔", label: t("nav.items.notifications"), href: "/notifications"},
        { icon: "⚙️", label: t("nav.items.settings"),      href: "/settings"     },
      ],
    },
  ];

  const handleLogout = () => {
    logout();
    onClose();
    router.push("/login");
  };

  const initials = user
    ? `${user.first_name?.[0] ?? ""}${user.last_name?.[0] ?? ""}`.toUpperCase() || "U"
    : "U";

  const handleNav = (href: string) => {
    onClose();
    router.push(href);
  };

  return (
    <div className="flex flex-col h-full bg-ink overflow-y-auto">
      {/* Header */}
      <div className="px-4 py-4 border-b border-white/10 flex items-center justify-between">
        <div className="font-syne font-black text-xl text-white tracking-tight">
          Med<span className="text-gold">Mind</span>
        </div>
        <button onClick={onClose} className="text-white/50 hover:text-white p-1 rounded">
          ✕
        </button>
      </div>

      {/* Search */}
      <div className="px-3 py-3 border-b border-white/10">
        <form onSubmit={(e) => { e.preventDefault(); if (searchQ.trim()) { handleNav(`/search?q=${encodeURIComponent(searchQ.trim())}`); }}}>
          <div className="relative">
            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-white/30 text-xs">🔍</span>
            <input
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              placeholder={t("nav.search_placeholder")}
              className="w-full bg-white/10 text-white text-sm placeholder:text-white/30 rounded-lg pl-7 pr-3 py-2 focus:outline-none focus:bg-white/15"
            />
          </div>
        </form>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-3">
        {/* Admin */}
        {user?.role === "admin" && (
          <div className="mb-3">
            <div className="text-white/30 font-syne font-bold text-[10px] tracking-widest uppercase px-2 mb-1">Admin</div>
            <button onClick={() => handleNav("/admin")} className={clsx("nav-item w-full text-left", pathname.startsWith("/admin") && "active")}>
              <span>🛠️</span> {t("nav.items.admin_panel")}
            </button>
          </div>
        )}
        {/* Teacher */}
        {(user?.role === "teacher" || user?.role === "doctor" || user?.role === "admin") && (
          <div className="mb-3">
            <div className="text-white/30 font-syne font-bold text-[10px] tracking-widest uppercase px-2 mb-1">{t("nav.sections.teaching")}</div>
            {[
              { icon: "🏠", label: t("nav.items.teacher_dashboard"), href: "/teacher/dashboard" },
              { icon: "✏️", label: t("nav.items.my_lessons"),        href: "/teacher/modules"   },
              { icon: "📰", label: t("nav.items.my_articles"),       href: "/teacher/articles"  },
              { icon: "📊", label: t("nav.items.analytics"),         href: "/teacher/analytics" },
              { icon: "💳", label: "Credits",                         href: "/teacher/credits"   },
            ].map(item => (
              <button key={item.href} onClick={() => handleNav(item.href)} className={clsx("nav-item w-full text-left", pathname.startsWith(item.href) && "active")}>
                <span>{item.icon}</span> {item.label}
              </button>
            ))}
          </div>
        )}
        {NAV_SECTIONS.map(section => (
          <div key={section.label} className="mb-3">
            <div className="text-white/30 font-syne font-bold text-[10px] tracking-widest uppercase px-2 mb-1">{section.label}</div>
            {section.items.map(item => (
              <button key={item.href} onClick={() => handleNav(item.href)} className={clsx("nav-item w-full text-left", pathname.startsWith(item.href) && "active")}>
                <span className="text-base w-5 text-center">{item.icon}</span>
                {item.label}
              </button>
            ))}
          </div>
        ))}
      </nav>

      {/* User footer */}
      <div className="px-3 py-4 border-t border-white/10">
        <div className="flex items-center gap-2.5 mb-3">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-gold to-amber-500 flex items-center justify-center font-syne font-bold text-ink text-sm flex-shrink-0">
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-syne font-bold text-white text-sm truncate">{user?.first_name} {user?.last_name}</div>
            <div className="text-white/40 text-xs capitalize">{user?.subscription_tier} · {user?.role}</div>
          </div>
          <button onClick={toggleDarkMode} className="text-white/40 hover:text-white/80 text-sm">{darkMode ? "☀️" : "🌙"}</button>
        </div>
        {/* XP */}
        <div className="mb-3">
          <div className="flex justify-between text-[10px] font-syne text-white/40 mb-1">
            <span>Lv. {user?.level ?? 1}</span>
            <span>{user?.xp ?? 0} XP</span>
          </div>
          <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
            <div className="h-full bg-gold rounded-full" style={{ width: `${Math.min(((user?.xp ?? 0) % 500) / 5, 100)}%` }} />
          </div>
        </div>
        <div className="flex gap-2">
          {user?.subscription_tier === "free" && (
            <button onClick={() => handleNav("/upgrade")} className="flex-1 bg-gold/20 border border-gold/40 text-gold text-xs font-syne font-bold py-2 rounded-lg">
              {t("nav.upgrade_cta")}
            </button>
          )}
          <button onClick={handleLogout} className="px-3 py-2 bg-white/10 hover:bg-white/20 text-white/60 hover:text-white text-xs font-syne rounded-lg transition-colors">
            {t("nav.logout")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Mobile top header ─────────────────────────────────────────────────────────
function MobileHeader({ onMenuOpen }: { onMenuOpen: () => void }) {
  const { user } = useAuthStore();
  const t = useT();
  return (
    <header className="md:hidden flex items-center gap-3 px-4 py-3 bg-ink border-b border-white/10 flex-shrink-0 z-40">
      <button
        onClick={onMenuOpen}
        className="text-white/70 hover:text-white p-1.5 rounded-lg hover:bg-white/10 transition-colors"
        aria-label="Open menu"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>
      <div className="font-syne font-black text-lg text-white tracking-tight">
        Med<span className="text-gold">Mind</span>
      </div>
      <div className="ml-auto flex items-center gap-2">
        {user?.subscription_tier === "free" && (
          <Link href="/upgrade" className="text-gold text-xs font-syne font-bold px-2 py-1 rounded bg-gold/10 border border-gold/30">
            Pro
          </Link>
        )}
        <NotificationBell />
      </div>
    </header>
  );
}

// ── Mobile bottom tab bar ─────────────────────────────────────────────────────
function MobileBottomNav() {
  const pathname = usePathname();
  const t = useT();
  return (
    <nav className="md:hidden flex items-center bg-ink border-t border-white/10 flex-shrink-0 z-40 safe-area-pb">
      {BOTTOM_TABS.map(tab => {
        const active = pathname.startsWith(tab.href);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={clsx(
              "flex-1 flex flex-col items-center justify-center py-2 gap-0.5 transition-colors min-h-[52px]",
              active ? "text-gold" : "text-white/40 hover:text-white/70"
            )}
          >
            <span className="text-xl leading-none">{tab.icon}</span>
            <span className={clsx("text-[9px] font-syne font-bold leading-none", active ? "text-gold" : "text-white/40")}>
              {t(tab.labelKey).split(" ")[0]}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}

// ── Main export: wraps the app layout on mobile ───────────────────────────────
export function MobileNavWrapper({ children }: { children: React.ReactNode }) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!drawerOpen) return;
    const handler = (e: MouseEvent) => {
      if (drawerRef.current && !drawerRef.current.contains(e.target as Node)) {
        setDrawerOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [drawerOpen]);

  // Prevent body scroll when drawer open
  useEffect(() => {
    document.body.style.overflow = drawerOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [drawerOpen]);

  return (
    <>
      {/* Mobile header (top bar) */}
      <MobileHeader onMenuOpen={() => setDrawerOpen(true)} />

      {/* Drawer overlay */}
      {drawerOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setDrawerOpen(false)} />
          {/* Drawer panel */}
          <div ref={drawerRef} className="relative w-72 max-w-[85vw] h-full shadow-2xl animate-slide-in-left">
            <DrawerNav onClose={() => setDrawerOpen(false)} />
          </div>
        </div>
      )}

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden min-h-0">
        {children}
      </main>

      {/* Bottom tab bar */}
      <MobileBottomNav />
    </>
  );
}
