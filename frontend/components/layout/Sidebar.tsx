"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { useAuthStore, useUIStore } from "@/lib/store";
import { NotificationBell } from "@/components/ui/NotificationBell";
import { clsx } from "clsx";

const NAV_SECTIONS = [
  {
    label: "Learning",
    items: [
      { icon: "🏠", label: "Dashboard", href: "/dashboard" },
      { icon: "📚", label: "Modules", href: "/modules" },
      { icon: "🤖", label: "AI Tutor", href: "/ai-tutor" },
      { icon: "🃏", label: "Flashcards", href: "/flashcards" },
      { icon: "🩺", label: "Cases", href: "/cases" },
    ],
  },
  {
    label: "Visual Medicine",
    items: [
      { icon: "🩻", label: "Imaging Library", href: "/imaging" },
      { icon: "🧊", label: "3D Anatomy", href: "/anatomy" },
    ],
  },
  {
    label: "Tools",
    items: [
      { icon: "💊", label: "Drug Database", href: "/drugs" },
      { icon: "📈", label: "Progress", href: "/progress" },
      { icon: "🏆", label: "Leaderboard", href: "/leaderboard" },
      { icon: "🎯", label: "For You", href: "/recommendations" },
    ],
  },
  {
    label: "Account",
    items: [
      { icon: "🏅", label: "Achievements", href: "/achievements" },
      { icon: "🔖", label: "Bookmarks", href: "/bookmarks" },
      { icon: "🔔", label: "Notifications", href: "/notifications" },
      { icon: "🔒", label: "Privacy", href: "/compliance" },
      { icon: "⚙️", label: "Settings", href: "/settings" },
    ],
  },
];

const ADMIN_NAV = { icon: "🛠️", label: "Admin Panel", href: "/admin" };
const TEACHER_NAV = { icon: "✏️", label: "My Lessons", href: "/teacher/modules" };
const TEACHER_COURSES_NAV = { icon: "📚", label: "My Courses", href: "/teacher/courses" };
const TEACHER_ANALYTICS_NAV = { icon: "📊", label: "Analytics", href: "/teacher/analytics" };

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthStore();
  const { darkMode, toggleDarkMode } = useUIStore();
  const [searchQ, setSearchQ] = useState("");

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
              placeholder="Search modules..."
              className="w-full bg-white/10 text-white text-sm placeholder:text-white/30 rounded-lg pl-7 pr-3 py-1.5 focus:outline-none focus:bg-white/15 transition-colors"
            />
          </div>
        </form>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2.5 py-4">
        {/* Admin link — only if role=admin */}
        {user?.role === "admin" && (
          <div className="mb-4">
            <div className="text-white/30 font-syne font-bold text-[10px] tracking-widest uppercase px-2 mb-1.5">Admin</div>
            <Link
              href={ADMIN_NAV.href}
              className={`nav-item ${pathname.startsWith(ADMIN_NAV.href) ? "active" : ""}`}
            >
              <span className="text-base w-5 text-center">{ADMIN_NAV.icon}</span>
              {ADMIN_NAV.label}
            </Link>
          </div>
        )}
        {/* Teacher authoring link */}
        {(user?.role === "teacher" || user?.role === "admin") && (
          <div className="mb-4">
            <div className="text-white/30 font-syne font-bold text-[10px] tracking-widest uppercase px-2 mb-1.5">Teaching</div>
            {[TEACHER_NAV, TEACHER_COURSES_NAV, TEACHER_ANALYTICS_NAV].map((item) => (
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
                  className={clsx(
                    "nav-item",
                    active && "active"
                  )}
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
            title="Log out"
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
            <span>Level {user?.level ?? 1}</span>
            <span>{user?.xp ?? 0} XP</span>
          </div>
          <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-gold transition-all duration-500 rounded-full"
              style={{ width: `${Math.min(((user?.xp ?? 0) % 500) / 5, 100)}%` }}
            />
          </div>
        </div>
        {/* Upgrade CTA for free users */}
        {user?.subscription_tier === "free" && (
          <Link
            href="/upgrade"
            className="mt-3 w-full block text-center bg-gold/20 hover:bg-gold/30 border border-gold/40 text-gold text-xs font-syne font-bold py-1.5 rounded-lg transition-colors"
          >
            ⚡ Upgrade Plan
          </Link>
        )}
      </div>
    </aside>
  );
}
