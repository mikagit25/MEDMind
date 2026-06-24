"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useEffect, useRef } from "react";
import { useAuthStore, useUIStore } from "@/lib/store";
import { NotificationBell } from "@/components/ui/NotificationBell";
import { clsx } from "clsx";
import { useT } from "@/lib/i18n";
import {
  LayoutDashboard, BookOpen, GraduationCap, Bot, Layers, BookMarked, MessageSquare,
  ClipboardList, Stethoscope, Building2, ScanLine, Box, Newspaper,
  Pill, PawPrint, TrendingUp, Trophy, Target, Award, Bookmark, Bell,
  Shield, Settings, Settings2, PenLine, BarChart2, CreditCard,
  Search, Sun, Moon, LogOut, FileText, FileJson, Menu, X, Radio, Gift, CalendarCheck, Globe, Shuffle, Calculator,
  HeartPulse, HelpCircle, Send,
  type LucideProps,
} from "lucide-react";

type NavItem = { Icon: React.ComponentType<LucideProps>; label: string; href: string };

function NavIcon({ Icon }: { Icon: React.ComponentType<LucideProps> }) {
  return <Icon size={15} strokeWidth={1.75} className="flex-shrink-0" />;
}

const BOTTOM_TABS: { Icon: React.ComponentType<LucideProps>; labelKey: string; href: string }[] = [
  { Icon: LayoutDashboard, labelKey: "nav.items.dashboard", href: "/dashboard" },
  { Icon: BookOpen,        labelKey: "nav.items.modules",   href: "/modules"   },
  { Icon: Bot,             labelKey: "nav.items.ai_tutor",  href: "/ai-tutor"  },
  { Icon: ScanLine,        labelKey: "nav.items.imaging",   href: "/imaging"   },
  { Icon: Pill,            labelKey: "nav.items.drugs",     href: "/drugs"     },
];

function DrawerNav({ onClose }: { onClose: () => void }) {
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
        { Icon: LayoutDashboard, label: t("nav.items.dashboard"),   href: "/dashboard"     },
        { Icon: BookOpen,        label: t("nav.items.modules"),     href: "/modules"       },
        { Icon: GraduationCap,  label: t("nav.items.my_courses"),  href: "/my-courses"    },
        { Icon: Bot,             label: t("nav.items.ai_tutor"),    href: "/ai-tutor"      },
        { Icon: MessageSquare,   label: t("nav.items.ai_history"),  href: "/ai-history"    },
        { Icon: Layers,          label: t("nav.items.flashcards"),  href: "/flashcards"    },
        { Icon: BookMarked,      label: t("nav.items.my_cards"),        href: "/my-flashcards" },
        { Icon: Globe,           label: t("nav.items.community_cards"), href: "/my-flashcards/community" },
        { Icon: ClipboardList,   label: t("nav.items.quiz"),        href: "/quiz"          },
        { Icon: Stethoscope,     label: t("nav.items.cases"),       href: "/cases"         },
        { Icon: Building2,       label: t("nav.items.simulation"),  href: "/simulation"    },
      ],
    },
    {
      label: t("nav.sections.visual_medicine"),
      items: [
        { Icon: ScanLine, label: t("nav.items.imaging"),    href: "/imaging" },
        { Icon: Box,      label: t("nav.items.anatomy_3d"), href: "/anatomy" },
      ],
    },
    {
      label: t("nav.sections.tools"),
      items: [
        { Icon: Newspaper,  label: t("nav.items.articles"),    href: "/knowledge"       },
        { Icon: Radio,      label: t("nav.items.news"),        href: "/news"            },
        { Icon: Pill,       label: t("nav.items.drugs"),        href: "/drugs"           },
        { Icon: Shuffle,    label: t("nav.items.drug_checker"), href: "/drug-checker"    },
        { Icon: HeartPulse, label: t("nav.items.health_hub"),   href: "/health"          },
        { Icon: Calculator, label: t("nav.items.calc_history"), href: "/calculators"     },
        { Icon: PenLine,    label: t("nav.items.my_notes"),     href: "/my-notes"        },
        { Icon: PawPrint,   label: t("nav.items.veterinary"),  href: "/veterinary"      },
        { Icon: TrendingUp,  label: t("nav.items.progress"),     href: "/progress"        },
        { Icon: Trophy,      label: t("nav.items.leaderboard"), href: "/leaderboard"     },
        { Icon: Target,      label: t("nav.items.for_you"),     href: "/recommendations" },
        { Icon: Send,        label: t("nav.items.telegram_bot"), href: "/bots"           },
        { Icon: HelpCircle,  label: t("nav.items.how_it_works"), href: "/how-it-works"  },
      ],
    },
    {
      label: t("nav.sections.account"),
      items: [
        { Icon: Award,         label: t("nav.items.achievements"),  href: "/achievements" },
        { Icon: Bookmark,      label: t("nav.items.bookmarks"),     href: "/bookmarks"    },
        { Icon: Bell,          label: t("nav.items.notifications"), href: "/notifications"},
        { Icon: CalendarCheck, label: t("nav.items.study_plan"),    href: "/study-plan"   },
        { Icon: Gift,          label: t("nav.items.referral"),      href: "/referral"     },
        { Icon: FileJson,      label: t("nav.items.fhir_export"),   href: "/fhir-export"  },
        { Icon: Shield,        label: t("nav.items.privacy"),       href: "/compliance"   },
        { Icon: Settings,      label: t("nav.items.settings"),      href: "/settings"     },
      ],
    },
  ];

  const TEACHER_ITEMS: NavItem[] = [
    { Icon: LayoutDashboard, label: t("nav.items.teacher_dashboard"), href: "/teacher/dashboard" },
    { Icon: PenLine,         label: t("nav.items.my_lessons"),        href: "/teacher/modules"   },
    { Icon: FileText,        label: t("nav.items.my_articles"),       href: "/teacher/articles"  },
    { Icon: Radio,           label: t("nav.items.my_news"),           href: "/teacher/news"      },
    { Icon: BarChart2,       label: t("nav.items.analytics"),         href: "/teacher/analytics" },
    { Icon: CreditCard,      label: t("nav.items.credits"),           href: "/teacher/credits"   },
  ];

  const handleLogout = () => { logout(); onClose(); router.push("/login"); };
  const handleNav = (href: string) => { onClose(); router.push(href); };
  const initials = user
    ? `${user.first_name?.[0] ?? ""}${user.last_name?.[0] ?? ""}`.toUpperCase() || "U"
    : "U";

  return (
    <div className="flex flex-col h-full bg-ink overflow-y-auto">
      {/* Header */}
      <div className="px-4 py-4 border-b border-white/10 flex items-center justify-between">
        <Link href="/" onClick={onClose} className="font-syne font-black text-xl text-white tracking-tight hover:opacity-80 transition-opacity">
          Med<span className="text-gold">Mind</span>
        </Link>
        <button onClick={onClose} className="text-white/50 hover:text-white p-1 rounded transition-colors">
          <X size={18} strokeWidth={1.75} />
        </button>
      </div>

      {/* Search */}
      <div className="px-3 py-3 border-b border-white/10">
        <form onSubmit={(e) => { e.preventDefault(); if (searchQ.trim()) handleNav(`/search?q=${encodeURIComponent(searchQ.trim())}`); }}>
          <div className="relative">
            <Search size={13} strokeWidth={2} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-white/30" />
            <input value={searchQ} onChange={(e) => setSearchQ(e.target.value)}
              placeholder={t("nav.search_placeholder")}
              className="w-full bg-white/10 text-white text-sm placeholder:text-white/30 rounded-lg pl-7 pr-3 py-2 focus:outline-none focus:bg-white/15" />
          </div>
        </form>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-3">
        {user?.role === "admin" && (
          <div className="mb-3">
            <div className="text-white/30 font-syne font-bold text-[10px] tracking-widest uppercase px-2 mb-1">Admin</div>
            <button onClick={() => handleNav("/admin")} className={clsx("nav-item w-full text-left", pathname.startsWith("/admin") && "active")}>
              <NavIcon Icon={Settings2} /> {t("nav.items.admin_panel")}
            </button>
          </div>
        )}
        {(user?.role === "teacher" || user?.role === "doctor" || user?.role === "admin") && (
          <div className="mb-3">
            <div className="text-white/30 font-syne font-bold text-[10px] tracking-widest uppercase px-2 mb-1">{t("nav.sections.teaching")}</div>
            {TEACHER_ITEMS.map(item => (
              <button key={item.href} onClick={() => handleNav(item.href)}
                className={clsx("nav-item w-full text-left", pathname.startsWith(item.href) && "active")}>
                <NavIcon Icon={item.Icon} /> {item.label}
              </button>
            ))}
          </div>
        )}
        {NAV_SECTIONS.map(section => (
          <div key={section.label} className="mb-3">
            <div className="text-white/30 font-syne font-bold text-[10px] tracking-widest uppercase px-2 mb-1">{section.label}</div>
            {section.items.map(item => (
              <button key={item.href} onClick={() => handleNav(item.href)}
                className={clsx("nav-item w-full text-left", pathname.startsWith(item.href) && "active")}>
                <NavIcon Icon={item.Icon} /> {item.label}
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
          <button onClick={toggleDarkMode} className="text-white/40 hover:text-white/80 transition-colors">
            {darkMode ? <Sun size={14} strokeWidth={1.75} /> : <Moon size={14} strokeWidth={1.75} />}
          </button>
        </div>
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
          <button onClick={handleLogout} className="flex items-center gap-1.5 px-3 py-2 bg-white/10 hover:bg-white/20 text-white/60 hover:text-white text-xs font-syne rounded-lg transition-colors">
            <LogOut size={12} strokeWidth={1.75} /> {t("nav.logout")}
          </button>
        </div>
      </div>
    </div>
  );
}

function MobileHeader({ onMenuOpen }: { onMenuOpen: () => void }) {
  const { user } = useAuthStore();
  const t = useT();
  return (
    <header className="md:hidden flex items-center gap-3 px-4 py-3 bg-ink border-b border-white/10 flex-shrink-0 z-40">
      <button onClick={onMenuOpen} className="text-white/70 hover:text-white p-1.5 rounded-lg hover:bg-white/10 transition-colors" aria-label="Open menu">
        <Menu size={20} strokeWidth={1.75} />
      </button>
      <Link href="/" className="font-syne font-black text-lg text-white tracking-tight hover:opacity-80 transition-opacity">
        Med<span className="text-gold">Mind</span>
      </Link>
      <div className="ml-auto flex items-center gap-2">
        {user?.subscription_tier === "free" && (
          <Link href="/upgrade" className="text-gold text-xs font-syne font-bold px-2 py-1 rounded bg-gold/10 border border-gold/30">Pro</Link>
        )}
        <NotificationBell />
      </div>
    </header>
  );
}

function MobileBottomNav() {
  const pathname = usePathname();
  const t = useT();
  return (
    <nav className="md:hidden flex items-center bg-ink border-t border-white/10 flex-shrink-0 z-40 safe-area-pb">
      {BOTTOM_TABS.map(tab => {
        const active = pathname.startsWith(tab.href);
        return (
          <Link key={tab.href} href={tab.href}
            className={clsx("flex-1 flex flex-col items-center justify-center py-2 gap-0.5 transition-colors min-h-[52px]",
              active ? "text-gold" : "text-white/40 hover:text-white/70")}>
            <tab.Icon size={20} strokeWidth={active ? 2 : 1.75} />
            <span className={clsx("text-[9px] font-syne font-bold leading-none", active ? "text-gold" : "text-white/40")}>
              {t(tab.labelKey as any).split(" ")[0]}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}

export function MobileNavWrapper({ children }: { children: React.ReactNode }) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!drawerOpen) return;
    const handler = (e: MouseEvent) => {
      if (drawerRef.current && !drawerRef.current.contains(e.target as Node)) setDrawerOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [drawerOpen]);

  useEffect(() => {
    document.body.style.overflow = drawerOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [drawerOpen]);

  return (
    <>
      <MobileHeader onMenuOpen={() => setDrawerOpen(true)} />
      {drawerOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setDrawerOpen(false)} />
          <div ref={drawerRef} className="relative w-72 max-w-[85vw] h-full shadow-2xl animate-slide-in-left">
            <DrawerNav onClose={() => setDrawerOpen(false)} />
          </div>
        </div>
      )}
      <main className="flex-1 flex flex-col overflow-hidden min-h-0">
        {children}
      </main>
      <MobileBottomNav />
    </>
  );
}
