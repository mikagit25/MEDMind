"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { useAuthStore, useUIStore } from "@/lib/store";
import { NotificationBell } from "@/components/ui/NotificationBell";
import { clsx } from "clsx";
import { useT } from "@/lib/i18n";
import {
  LayoutDashboard, BookOpen, GraduationCap, Bot, Layers, BookMarked,
  ClipboardList, Stethoscope, Building2, ScanLine, Box, Newspaper,
  Pill, PawPrint, TrendingUp, Trophy, Target, Award, Bookmark, Bell,
  Shield, Settings, Settings2, PenLine, BarChart2, CreditCard,
  Search, Sun, Moon, LogOut, FileText, Radio, Gift, CalendarCheck, Users, Globe, Shuffle, Calculator,
  type LucideProps,
} from "lucide-react";

type NavItem = { icon: React.ComponentType<LucideProps>; label: string; href: string };

function NavIcon({ Icon }: { Icon: React.ComponentType<LucideProps> }) {
  return <Icon size={15} strokeWidth={1.75} className="flex-shrink-0" />;
}

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthStore();
  const { darkMode, toggleDarkMode } = useUIStore();
  const [searchQ, setSearchQ] = useState("");
  const t = useT();

  const NAV_SECTIONS: { label: string; items: NavItem[] }[] = [
    {
      label: t("nav.sections.learning"),
      items: [
        { icon: LayoutDashboard, label: t("nav.items.dashboard"),   href: "/dashboard" },
        { icon: BookOpen,        label: t("nav.items.modules"),      href: "/modules" },
        { icon: GraduationCap,  label: t("nav.items.my_courses"),   href: "/my-courses" },
        { icon: Bot,             label: t("nav.items.ai_tutor"),     href: "/ai-tutor" },
        { icon: Layers,          label: t("nav.items.flashcards"),   href: "/flashcards" },
        { icon: BookMarked,      label: t("nav.items.my_cards"),        href: "/my-flashcards" },
        { icon: Globe,           label: t("nav.items.community_cards"), href: "/my-flashcards/community" },
        { icon: ClipboardList,   label: t("nav.items.quiz"),         href: "/quiz" },
        { icon: Stethoscope,     label: t("nav.items.cases"),        href: "/cases" },
        { icon: Building2,       label: t("nav.items.simulation"),   href: "/simulation" },
      ],
    },
    {
      label: t("nav.sections.visual_medicine"),
      items: [
        { icon: ScanLine, label: t("nav.items.imaging"),    href: "/imaging" },
        { icon: Box,      label: t("nav.items.anatomy_3d"), href: "/anatomy" },
      ],
    },
    {
      label: t("nav.sections.tools"),
      items: [
        { icon: Newspaper,   label: t("nav.items.articles"),    href: "/knowledge" },
        { icon: Radio,       label: t("nav.items.news"),         href: "/news" },
        { icon: Pill,        label: t("nav.items.drugs"),         href: "/drugs" },
        { icon: Shuffle,     label: t("nav.items.drug_checker"),  href: "/drug-checker" },
        { icon: Calculator,  label: t("nav.items.calc_history"),  href: "/calculators" },
        { icon: PawPrint,    label: t("nav.items.veterinary"),   href: "/veterinary" },
        { icon: TrendingUp,  label: t("nav.items.progress"),     href: "/progress" },
        { icon: Trophy,      label: t("nav.items.leaderboard"),  href: "/leaderboard" },
        { icon: Target,      label: t("nav.items.for_you"),      href: "/recommendations" },
      ],
    },
    {
      label: t("nav.sections.account"),
      items: [
        { icon: Award,         label: t("nav.items.achievements"),  href: "/achievements" },
        { icon: Bookmark,      label: t("nav.items.bookmarks"),     href: "/bookmarks" },
        { icon: Bell,          label: t("nav.items.notifications"), href: "/notifications" },
        { icon: CalendarCheck, label: t("nav.items.study_plan"),    href: "/study-plan" },
        { icon: Gift,          label: t("nav.items.referral"),      href: "/referral" },
        { icon: Shield,        label: t("nav.items.privacy"),       href: "/compliance" },
        { icon: Settings,      label: t("nav.items.settings"),      href: "/settings" },
      ],
    },
  ];

  const TEACHER_ITEMS: NavItem[] = [
    { icon: LayoutDashboard, label: t("nav.items.teacher_dashboard"), href: "/teacher/dashboard" },
    { icon: PenLine,         label: t("nav.items.my_lessons"),        href: "/teacher/modules" },
    { icon: BookOpen,        label: t("nav.items.teacher_courses"),   href: "/teacher/courses" },
    { icon: FileText,        label: t("nav.items.my_articles"),       href: "/teacher/articles" },
    { icon: Radio,           label: t("nav.items.my_news"),           href: "/teacher/news" },
    { icon: BarChart2,       label: t("nav.items.analytics"),         href: "/teacher/analytics" },
    { icon: CreditCard,      label: t("nav.items.credits"),           href: "/teacher/credits" },
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
        <Link href="/" className="font-syne font-black text-2xl text-white tracking-tight hover:opacity-80 transition-opacity">
          Med<span className="text-gold">Mind</span>
          <span className="text-xs text-white/30 font-semibold tracking-widest ml-1.5 uppercase block mt-0.5">
            AI Platform
          </span>
        </Link>
      </div>

      {/* Search */}
      <div className="px-3 py-3 border-b border-white/10">
        <form onSubmit={(e) => {
          e.preventDefault();
          if (searchQ.trim()) router.push(`/search?q=${encodeURIComponent(searchQ.trim())}`);
        }}>
          <div className="relative">
            <Search size={13} strokeWidth={2} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-white/30" />
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
        {/* Admin */}
        {user?.role === "admin" && (
          <div className="mb-4">
            <div className="text-white/30 font-syne font-bold text-[10px] tracking-widest uppercase px-2 mb-1.5">
              {t("nav.sections.admin")}
            </div>
            <Link href="/admin" className={`nav-item ${pathname.startsWith("/admin") ? "active" : ""}`}>
              <NavIcon Icon={Settings2} />
              {t("nav.items.admin_panel")}
            </Link>
          </div>
        )}

        {/* Teacher */}
        {(user?.role === "teacher" || user?.role === "doctor" || user?.role === "admin") && (
          <div className="mb-4">
            <div className="text-white/30 font-syne font-bold text-[10px] tracking-widest uppercase px-2 mb-1.5">
              {t("nav.sections.teaching")}
            </div>
            {TEACHER_ITEMS.map((item) => (
              <Link key={item.href} href={item.href}
                className={clsx("nav-item", pathname.startsWith(item.href) && "active")}>
                <NavIcon Icon={item.icon} />
                {item.label}
              </Link>
            ))}
          </div>
        )}

        {/* Main sections */}
        {NAV_SECTIONS.map((section) => (
          <div key={section.label} className="mb-4">
            <div className="text-white/30 font-syne font-bold text-[10px] tracking-widest uppercase px-2 mb-1.5">
              {section.label}
            </div>
            {section.items.map((item) => (
              <Link key={item.href} href={item.href}
                className={clsx("nav-item", pathname.startsWith(item.href) && "active")}>
                <NavIcon Icon={item.icon} />
                {item.label}
              </Link>
            ))}
          </div>
        ))}

        {/* Clinic: Team */}
        {(user?.subscription_tier === "clinic" || user?.role === "admin") && (
          <div className="mb-4">
            <div className="text-white/30 font-syne font-bold text-[10px] tracking-widest uppercase px-2 mb-1.5">
              Clinic
            </div>
            <Link href="/team" className={clsx("nav-item", pathname.startsWith("/team") && "active")}>
              <NavIcon Icon={Users} />
              {t("nav.items.team")}
            </Link>
          </div>
        )}
      </nav>

      {/* User footer */}
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
          <button onClick={handleLogout} title={t("nav.logout")}
            className="text-white/30 hover:text-white/70 transition-colors">
            <LogOut size={14} strokeWidth={1.75} />
          </button>
          <button onClick={toggleDarkMode} title={t("settings.dark_mode")}
            className="text-white/30 hover:text-white/70 transition-colors ml-0.5">
            {darkMode ? <Sun size={14} strokeWidth={1.75} /> : <Moon size={14} strokeWidth={1.75} />}
          </button>
        </div>

        {/* XP Bar */}
        <div className="mt-3">
          <div className="flex justify-between text-[10px] font-syne text-white/40 mb-1">
            <span>{t("common.level")} {user?.level ?? 1}</span>
            <span>{user?.xp ?? 0} {t("common.xp")}</span>
          </div>
          <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
            <div className="h-full bg-gold transition-all duration-500 rounded-full"
              style={{ width: `${Math.min(((user?.xp ?? 0) % 500) / 5, 100)}%` }} />
          </div>
        </div>

        {/* Upgrade CTA */}
        {user?.subscription_tier === "free" && (
          <Link href="/upgrade"
            className="mt-3 w-full block text-center bg-gold/20 hover:bg-gold/30 border border-gold/40 text-gold text-xs font-syne font-bold py-1.5 rounded-lg transition-colors">
            {t("nav.upgrade_cta")}
          </Link>
        )}
      </div>
    </aside>
  );
}
