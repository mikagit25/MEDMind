"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { useAuthStore, useUIStore } from "@/lib/store";
import { NotificationBell } from "@/components/ui/NotificationBell";
import { clsx } from "clsx";
import { useT } from "@/lib/i18n";

export function Sidebar() {
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
        { icon: "🏠", label: t("nav.items.dashboard"), href: "/dashboard" },
        { icon: "📚", label: t("nav.items.modules"), href: "/modules" },
        { icon: "🎓", label: t("nav.items.my_courses"), href: "/my-courses" },
        { icon: "🤖", label: t("nav.items.ai_tutor"), href: "/ai-tutor" },
        { icon: "🃏", label: t("nav.items.flashcards"), href: "/flashcards" },
        { icon: "📇", label: t("nav.items.my_cards"), href: "/my-flashcards" },
        { icon: "📝", label: t("nav.items.quiz"), href: "/quiz" },
        { icon: "🩺", label: t("nav.items.cases"), href: "/cases" },
        { icon: "🏥", label: t("nav.items.simulation"), href: "/simulation" },
      ],
    },
    {
      label: t("nav.sections.visual_medicine"),
      items: [
        { icon: "🩻", label: t("nav.items.imaging"), href: "/imaging" },
        { icon: "🧊", label: t("nav.items.anatomy_3d"), href: "/anatomy" },
      ],
    },
    {
      label: t("nav.sections.tools"),
      items: [
        { icon: "💊", label: t("nav.items.drugs"), href: "/drugs" },
        { icon: "🐾", label: t("nav.items.veterinary"), href: "/veterinary" },
        { icon: "📈", label: t("nav.items.progress"), href: "/progress" },
        { icon: "🏆", label: t("nav.items.leaderboard"), href: "/leaderboard" },
        { icon: "🎯", label: t("nav.items.for_you"), href: "/recommendations" },
      ],
    },
    {
      label: t("nav.sections.account"),
      items: [
        { icon: "🏅", label: t("nav.items.achievements"), href: "/achievements" },
        { icon: "🔖", label: t("nav.items.bookmarks"), href: "/bookmarks" },
        { icon: "🔔", label: t("nav.items.notifications"), href: "/notifications" },
        { icon: "🔒", label: t("nav.items.privacy"), href: "/compliance" },
        { icon: "⚙️", label: t("nav.items.settings"), href: "/settings" },
      ],
    },
  ];

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  const initials = user
    ? `${user.first_name?.[0] ?? ""}${user.last_name?.[0] ?? ""}`.toUpperCase() || "U"
    : "U";

  return (
    <aside className="w-64 bg-ink flex flex-col flex-shrink-0 overflow-y-auto">
      {/* Logo */}
      <div className="px-5 py-6 border-b border-white/10">
        <div className="font-syne font-black text-2xl text-white tracking-tight">
          Med<span className="text-gold">Mind</span>
          <span className="text-xs text-white/30 font-semibold tracking-widest ml-1.5 uppercase block mt-0.5">
            AI Platform
          </span>
        </div>
      </div>

      {/* Search */}
      <div className="px-3 py-3 border-b border-white/10">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (searchQ.trim()) router.push(`/search?q=${encodeURIComponent(searchQ.trim())}`);
          }}
        >
          <div className="relative">
            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-white/30 text-xs">🔍</span>
            <input
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              placeholder={t("nav.search_placeholder")}
              className="w-full bg-white/10 text-white text-sm placeholder:text-white/30 rounded-lg pl-7 pr-3 py-1.5 focus:outline-none focus:bg-white/15 transition-colors"
            />
          </div>
        </form>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2.5 py-4">
        {/* Admin link */}
        {user?.role === "admin" && (
          <div className="mb-4">
            <div className="text-white/30 font-syne font-bold text-[10px] tracking-widest uppercase px-2 mb-1.5">
              {t("nav.sections.admin")}
            </div>
            <Link
              href="/admin"
              className={`nav-item ${pathname.startsWith("/admin") ? "active" : ""}`}
            >
              <span className="text-base w-5 text-center">🛠️</span>
              {t("nav.items.admin_panel")}
            </Link>
          </div>
        )}
        {/* Teacher nav */}
        {(user?.role === "teacher" || user?.role === "admin") && (
          <div className="mb-4">
            <div className="text-white/30 font-syne font-bold text-[10px] tracking-widest uppercase px-2 mb-1.5">
              {t("nav.sections.teaching")}
            </div>
            {[
              { icon: "🏠", label: t("nav.items.teacher_dashboard"), href: "/teacher/dashboard" },
              { icon: "✏️", label: t("nav.items.my_lessons"), href: "/teacher/modules" },
              { icon: "📚", label: t("nav.items.teacher_courses"), href: "/teacher/courses" },
              { icon: "📊", label: t("nav.items.analytics"), href: "/teacher/analytics" },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`nav-item ${pathname.startsWith(item.href) ? "active" : ""}`}
              >
                <span className="text-base w-5 text-center">{item.icon}</span>
                {item.label}
              </Link>
            ))}
          </div>
        )}
        {NAV_SECTIONS.map((section) => (
          <div key={section.label} className="mb-4">
            <div className="text-white/30 font-syne font-bold text-[10px] tracking-widest uppercase px-2 mb-1.5">
              {section.label}
            </div>
            {section.items.map((item) => {
              const active = pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={clsx("nav-item", active && "active")}
                >
                  <span className="text-base w-5 text-center">{item.icon}</span>
                  {item.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* User */}
      <div className="px-3 py-4 border-t border-white/10">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-gold to-amber-2 flex items-center justify-center font-syne font-bold text-ink text-sm flex-shrink-0">
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-syne font-bold text-white text-sm truncate">
              {user?.first_name} {user?.last_name}
            </div>
            <div className="text-white/40 text-xs capitalize">
              {user?.subscription_tier} • {user?.role}
            </div>
          </div>
          <NotificationBell />
          <button
            onClick={handleLogout}
            className="text-white/30 hover:text-white/70 text-xs font-syne transition-colors"
            title={t("nav.logout")}
          >
            ←
          </button>
          <button
            onClick={toggleDarkMode}
            className="text-white/30 hover:text-white/70 text-xs transition-colors ml-0.5"
            title={darkMode ? "Light mode" : "Dark mode"}
          >
            {darkMode ? "☀️" : "🌙"}
          </button>
        </div>
        {/* XP Bar */}
        <div className="mt-3">
          <div className="flex justify-between text-[10px] font-syne text-white/40 mb-1">
            <span>{t("common.level")} {user?.level ?? 1}</span>
            <span>{user?.xp ?? 0} {t("common.xp")}</span>
          </div>
          <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-gold transition-all duration-500 rounded-full"
              style={{ width: `${Math.min(((user?.xp ?? 0) % 500) / 5, 100)}%` }}
            />
          </div>
        </div>
        {/* Upgrade CTA */}
        {user?.subscription_tier === "free" && (
          <Link
            href="/upgrade"
            className="mt-3 w-full block text-center bg-gold/20 hover:bg-gold/30 border border-gold/40 text-gold text-xs font-syne font-bold py-1.5 rounded-lg transition-colors"
          >
            {t("nav.upgrade_cta")}
          </Link>
        )}
      </div>
    </aside>
  );
}
