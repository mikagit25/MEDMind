"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { api, adminApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

type Stats = {
  users: { total: number; active: number; new_last_7_days: number; by_tier: Record<string, number> };
  content: { modules_total: number; modules_published: number; lessons: number; flashcards: number; mcq: number; cases: number };
  articles?: { total: number; published: number; pending_review: number };
};

type AdminUser = {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  role: string;
  subscription_tier: string;
  is_active: boolean;
  xp: number;
  level: number;
  created_at?: string;
};

type AdminModule = {
  id: string;
  code: string;
  title: string;
  specialty?: string;
  level: number;
  is_published: boolean;
  is_fundamental: boolean;
  is_veterinary: boolean;
  lessons: number;
  flashcards: number;
  mcq: number;
  cases: number;
};

type Tab = "overview" | "users" | "modules" | "generate" | "articles" | "translations" | "flags" | "system" | "audit";

const TIERS = ["free", "student", "pro", "clinic", "lifetime"];
const ROLES = ["student", "teacher", "doctor", "admin"];
const TIER_COLORS: Record<string, string> = {
  free: "bg-surface-2 text-ink-3 border-border",
  student: "bg-blue-light text-blue border-blue/20",
  pro: "bg-amber-light text-amber border-amber/20",
  clinic: "bg-green-light text-green border-green/20",
  lifetime: "bg-ink text-white border-ink",
};

export default function AdminPage() {
  const { user } = useAuthStore();
  const router = useRouter();

  const [tab, setTab] = useState<Tab>("overview");
  const [stats, setStats] = useState<Stats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [modules, setModules] = useState<AdminModule[]>([]);
  const [userSearch, setUserSearch] = useState("");
  const [userTierFilter, setUserTierFilter] = useState("");
  const [moduleSearch, setModuleSearch] = useState("");
  const [modulePublished, setModulePublished] = useState<"" | "true" | "false">("");
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<{ msg: string; type: "ok" | "err" } | null>(null);

  // Guard: only admin
  useEffect(() => {
    if (user && user.role !== "admin") {
      router.replace("/dashboard");
    }
  }, [user, router]);

  const showToast = (msg: string, type: "ok" | "err" = "ok") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  // Load stats
  useEffect(() => {
    api.get("/admin/stats").then((r) => setStats(r.data)).catch(() => {});
  }, []);

  // Load users
  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = { limit: "100" };
      if (userSearch) params.search = userSearch;
      if (userTierFilter) params.tier = userTierFilter;
      const r = await api.get("/admin/users", { params });
      setUsers(r.data.users ?? []);
    } catch {
      showToast("Failed to load users", "err");
    } finally {
      setLoading(false);
    }
  }, [userSearch, userTierFilter]);

  // Load modules
  const loadModules = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | boolean> = { limit: "500" };
      if (moduleSearch) params.search = moduleSearch;
      if (modulePublished !== "") params.published = modulePublished === "true";
      const r = await api.get("/admin/modules", { params });
      setModules(r.data.modules ?? []);
    } catch {
      showToast("Failed to load modules", "err");
    } finally {
      setLoading(false);
    }
  }, [moduleSearch, modulePublished]);

  useEffect(() => {
    if (tab === "users") loadUsers();
    if (tab === "modules") loadModules();
  }, [tab, loadUsers, loadModules]);

  const patchUser = async (userId: string, patch: Record<string, unknown>) => {
    try {
      const r = await api.patch(`/admin/users/${userId}`, patch);
      setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, ...r.data } : u)));
      showToast("User updated");
    } catch (e: any) {
      showToast(e.response?.data?.detail ?? "Update failed", "err");
    }
  };

  const togglePublish = async (mod: AdminModule) => {
    try {
      const r = await api.patch(`/admin/modules/${mod.id}`, { is_published: !mod.is_published });
      setModules((prev) => prev.map((m) => (m.id === mod.id ? { ...m, ...r.data } : m)));
      showToast(r.data.is_published ? "Module published" : "Module unpublished");
    } catch (e: any) {
      showToast(e.response?.data?.detail ?? "Update failed", "err");
    }
  };

  const bulkPublishAll = async (publish: boolean) => {
    const ids = modules.filter((m) => m.is_published !== publish).map((m) => m.id);
    if (!ids.length) return showToast("Nothing to change");
    try {
      await api.post("/admin/modules/bulk-publish", { ids, publish });
      setModules((prev) => prev.map((m) => (ids.includes(m.id) ? { ...m, is_published: publish } : m)));
      showToast(`${ids.length} modules ${publish ? "published" : "unpublished"}`);
    } catch (e: any) {
      showToast(e.response?.data?.detail ?? "Bulk update failed", "err");
    }
  };

  if (user?.role !== "admin") return null;

  return (
    <div className="flex-1 overflow-y-auto p-6">
      {/* Toast */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 px-4 py-2 rounded shadow font-syne font-semibold text-sm text-white animate-fade-up ${
            toast.type === "ok" ? "bg-green" : "bg-red"
          }`}
        >
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="mb-6">
        <h1 className="font-syne font-black text-2xl text-ink">Admin Panel</h1>
        <p className="text-ink-3 text-sm font-serif mt-0.5">Platform management & content control</p>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-1 mb-6 bg-surface border border-border rounded-lg p-1 w-fit">
        {([
          ["overview",     "📊 Overview"],
          ["users",        "👥 Users"],
          ["modules",      "📚 Modules"],
          ["generate",     "✨ Generate"],
          ["articles",     "📰 Articles"],
          ["translations", "🌐 Translations"],
          ["flags",        "🚩 Flags"],
          ["system",       "⚙️ System"],
          ["audit",        "🔍 Audit Log"],
        ] as [Tab, string][]).map(([t, label]) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`font-syne font-semibold text-sm px-4 py-1.5 rounded transition-colors ${
              tab === t ? "bg-ink text-white" : "text-ink-2 hover:text-ink"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* ── Overview ── */}
      {tab === "overview" && stats && (
        <div className="space-y-5">
          {/* User stats */}
          <section>
            <h2 className="font-syne font-bold text-sm text-ink-2 uppercase tracking-wider mb-3">Users</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: "Total users", val: stats.users.total },
                { label: "Active users", val: stats.users.active },
                { label: "New this week", val: stats.users.new_last_7_days },
                { label: "Paying users", val: Object.entries(stats.users.by_tier).filter(([k]) => k !== "free").reduce((a, [, v]) => a + v, 0) },
              ].map((s) => (
                <div key={s.label} className="card p-4 text-center">
                  <div className="font-syne font-black text-2xl text-ink">{s.val}</div>
                  <div className="text-ink-3 text-xs font-syne mt-1">{s.label}</div>
                </div>
              ))}
            </div>
          </section>

          {/* Tier breakdown */}
          <section>
            <h2 className="font-syne font-bold text-sm text-ink-2 uppercase tracking-wider mb-3">Users by Tier</h2>
            <div className="flex flex-wrap gap-2">
              {Object.entries(stats.users.by_tier).map(([tier, count]) => (
                <span key={tier} className={`border rounded-full px-3 py-1 font-syne font-semibold text-xs ${TIER_COLORS[tier] ?? "bg-surface-2 text-ink-3 border-border"}`}>
                  {tier}: {count}
                </span>
              ))}
            </div>
          </section>

          {/* Content stats */}
          <section>
            <h2 className="font-syne font-bold text-sm text-ink-2 uppercase tracking-wider mb-3">Content</h2>
            <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
              {[
                { label: "Modules", val: `${stats.content.modules_published}/${stats.content.modules_total}`, sub: "published" },
                { label: "Lessons", val: stats.content.lessons },
                { label: "Flashcards", val: stats.content.flashcards },
                { label: "MCQ", val: stats.content.mcq },
                { label: "Cases", val: stats.content.cases },
                { label: "Articles", val: `${stats.articles?.published ?? 0}/${stats.articles?.total ?? 0}`, sub: "published" },
              ].map((s) => (
                <div key={s.label} className="card p-4 text-center">
                  <div className="font-syne font-black text-xl text-ink">{s.val}</div>
                  {s.sub && <div className="text-ink-3 text-[10px] font-syne">{s.sub}</div>}
                  <div className="text-ink-3 text-xs font-syne mt-1">{s.label}</div>
                </div>
              ))}
            </div>
          </section>

          {/* Quick actions */}
          <section>
            <h2 className="font-syne font-bold text-sm text-ink-2 uppercase tracking-wider mb-3">Quick Actions</h2>
            <div className="flex gap-2 flex-wrap">
              <button onClick={() => setTab("users")} className="btn-primary text-xs">Manage Users</button>
              <button onClick={() => setTab("modules")} className="btn-primary text-xs">Manage Modules</button>
              <button
                onClick={() => setTab("articles")}
                className="relative btn-primary text-xs"
              >
                Review Articles
                {(stats.articles?.pending_review ?? 0) > 0 && (
                  <span className="absolute -top-1.5 -right-1.5 bg-amber text-white text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center">
                    {stats.articles!.pending_review}
                  </span>
                )}
              </button>
            </div>
          </section>
        </div>
      )}

      {/* ── Users ── */}
      {tab === "users" && (
        <div>
          {/* Filters */}
          <div className="flex gap-2 mb-4 flex-wrap">
            <input
              placeholder="Search email or name…"
              value={userSearch}
              onChange={(e) => setUserSearch(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && loadUsers()}
              className="border border-border rounded px-3 py-1.5 text-sm font-serif bg-bg focus:outline-none focus:border-ink w-64"
            />
            <select
              value={userTierFilter}
              onChange={(e) => setUserTierFilter(e.target.value)}
              className="border border-border rounded px-3 py-1.5 text-sm font-serif bg-bg focus:outline-none"
            >
              <option value="">All tiers</option>
              {TIERS.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
            <button onClick={loadUsers} className="btn-primary text-xs">Search</button>
          </div>

          {/* Table */}
          <div className="card overflow-hidden">
            {loading ? (
              <div className="p-8 text-center text-ink-3 text-sm font-serif">Loading…</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-surface-2">
                      <th className="text-left px-4 py-2.5 font-syne font-semibold text-ink-2 text-xs uppercase">User</th>
                      <th className="text-left px-4 py-2.5 font-syne font-semibold text-ink-2 text-xs uppercase">Tier</th>
                      <th className="text-left px-4 py-2.5 font-syne font-semibold text-ink-2 text-xs uppercase">Role</th>
                      <th className="text-left px-4 py-2.5 font-syne font-semibold text-ink-2 text-xs uppercase">XP</th>
                      <th className="text-left px-4 py-2.5 font-syne font-semibold text-ink-2 text-xs uppercase">Status</th>
                      <th className="text-left px-4 py-2.5 font-syne font-semibold text-ink-2 text-xs uppercase">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => (
                      <tr key={u.id} className="border-b border-border last:border-0 hover:bg-surface-2 transition-colors">
                        <td className="px-4 py-2.5">
                          <div className="font-syne font-semibold text-ink text-sm">{u.first_name} {u.last_name}</div>
                          <div className="text-ink-3 text-xs font-serif">{u.email}</div>
                        </td>
                        <td className="px-4 py-2.5">
                          <select
                            value={u.subscription_tier}
                            onChange={(e) => patchUser(u.id, { subscription_tier: e.target.value })}
                            className={`border rounded px-2 py-0.5 font-syne font-semibold text-xs cursor-pointer focus:outline-none ${TIER_COLORS[u.subscription_tier] ?? ""}`}
                          >
                            {TIERS.map((t) => <option key={t} value={t}>{t}</option>)}
                          </select>
                        </td>
                        <td className="px-4 py-2.5">
                          <select
                            value={u.role}
                            onChange={(e) => patchUser(u.id, { role: e.target.value })}
                            className="border border-border rounded px-2 py-0.5 font-syne text-xs focus:outline-none bg-bg text-ink"
                          >
                            {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                          </select>
                        </td>
                        <td className="px-4 py-2.5 font-syne font-semibold text-ink text-xs">{u.xp} xp</td>
                        <td className="px-4 py-2.5">
                          <span className={`font-syne font-semibold text-xs ${u.is_active ? "text-green" : "text-red"}`}>
                            {u.is_active ? "Active" : "Disabled"}
                          </span>
                        </td>
                        <td className="px-4 py-2.5">
                          <button
                            onClick={() => patchUser(u.id, { is_active: !u.is_active })}
                            className={`text-xs font-syne font-semibold border rounded px-2 py-0.5 transition-colors ${
                              u.is_active
                                ? "border-red/30 text-red hover:bg-red-light"
                                : "border-green/30 text-green hover:bg-green-light"
                            }`}
                          >
                            {u.is_active ? "Disable" : "Enable"}
                          </button>
                        </td>
                      </tr>
                    ))}
                    {!users.length && !loading && (
                      <tr>
                        <td colSpan={6} className="px-4 py-8 text-center text-ink-3 font-serif text-sm">No users found</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          <div className="text-ink-3 text-xs font-serif mt-2">{users.length} users shown</div>
        </div>
      )}

      {/* ── Modules ── */}
      {tab === "modules" && (
        <div>
          {/* Filters + bulk actions */}
          <div className="flex gap-2 mb-4 flex-wrap items-center">
            <input
              placeholder="Search modules…"
              value={moduleSearch}
              onChange={(e) => setModuleSearch(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && loadModules()}
              className="border border-border rounded px-3 py-1.5 text-sm font-serif bg-bg focus:outline-none focus:border-ink w-56"
            />
            <select
              value={modulePublished}
              onChange={(e) => setModulePublished(e.target.value as "" | "true" | "false")}
              className="border border-border rounded px-3 py-1.5 text-sm font-serif bg-bg focus:outline-none"
            >
              <option value="">All status</option>
              <option value="true">Published</option>
              <option value="false">Unpublished</option>
            </select>
            <button onClick={loadModules} className="btn-primary text-xs">Search</button>
            <div className="ml-auto flex gap-2">
              <button
                onClick={() => bulkPublishAll(true)}
                className="text-xs font-syne font-semibold border border-green/30 text-green hover:bg-green-light rounded px-3 py-1.5 transition-colors"
              >
                Publish All
              </button>
              <button
                onClick={() => bulkPublishAll(false)}
                className="text-xs font-syne font-semibold border border-red/30 text-red hover:bg-red-light rounded px-3 py-1.5 transition-colors"
              >
                Unpublish All
              </button>
            </div>
          </div>

          {/* Modules table */}
          <div className="card overflow-hidden">
            {loading ? (
              <div className="p-8 text-center text-ink-3 text-sm font-serif">Loading…</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-surface-2">
                      <th className="text-left px-4 py-2.5 font-syne font-semibold text-ink-2 text-xs uppercase">Module</th>
                      <th className="text-left px-4 py-2.5 font-syne font-semibold text-ink-2 text-xs uppercase">Specialty</th>
                      <th className="text-left px-4 py-2.5 font-syne font-semibold text-ink-2 text-xs uppercase">Content</th>
                      <th className="text-left px-4 py-2.5 font-syne font-semibold text-ink-2 text-xs uppercase">Flags</th>
                      <th className="text-left px-4 py-2.5 font-syne font-semibold text-ink-2 text-xs uppercase">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {modules.map((m) => (
                      <tr key={m.id} className="border-b border-border last:border-0 hover:bg-surface-2 transition-colors">
                        <td className="px-4 py-2.5">
                          <div className="font-syne font-semibold text-ink text-sm">{m.title}</div>
                          <div className="text-ink-3 text-xs font-mono">{m.code}</div>
                        </td>
                        <td className="px-4 py-2.5 text-ink-2 font-serif text-xs">{m.specialty ?? "—"}</td>
                        <td className="px-4 py-2.5">
                          <div className="flex gap-2 text-xs text-ink-3 font-syne flex-wrap">
                            <span title="Lessons">📖 {m.lessons}</span>
                            <span title="Flashcards">🃏 {m.flashcards}</span>
                            <span title="MCQ">❓ {m.mcq}</span>
                            <span title="Cases">🩺 {m.cases}</span>
                          </div>
                        </td>
                        <td className="px-4 py-2.5">
                          <div className="flex gap-1 flex-wrap">
                            {m.is_fundamental && (
                              <span className="text-[10px] bg-blue-light text-blue border border-blue/20 rounded-full px-1.5 py-0.5 font-syne font-semibold">Base</span>
                            )}
                            {m.is_veterinary && (
                              <span className="text-[10px] bg-amber-light text-amber border border-amber/20 rounded-full px-1.5 py-0.5 font-syne font-semibold">Vet</span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-2.5">
                          <button
                            onClick={() => togglePublish(m)}
                            className={`font-syne font-semibold text-xs border rounded px-2.5 py-0.5 transition-colors ${
                              m.is_published
                                ? "border-green/30 text-green bg-green-light hover:bg-green hover:text-white"
                                : "border-border text-ink-3 hover:border-ink hover:text-ink"
                            }`}
                          >
                            {m.is_published ? "✓ Published" : "Unpublished"}
                          </button>
                        </td>
                      </tr>
                    ))}
                    {!modules.length && !loading && (
                      <tr>
                        <td colSpan={5} className="px-4 py-8 text-center text-ink-3 font-serif text-sm">No modules found</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          <div className="text-ink-3 text-xs font-serif mt-2">
            {modules.length} modules — {modules.filter((m) => m.is_published).length} published
          </div>
        </div>
      )}

      {/* ── Generate Module ── */}
      {tab === "generate" && <GenerateModulePanel showToast={showToast} />}

      {/* ── Articles ── */}
      {tab === "articles" && <ArticlesPanel showToast={showToast} />}

      {/* ── Translations ── */}
      {tab === "translations" && <TranslationsPanel showToast={showToast} />}

      {/* ── Feature Flags ── */}
      {tab === "flags" && <FeatureFlagsPanel showToast={showToast} />}

      {/* ── System Health ── */}
      {tab === "system" && <SystemHealthPanel />}

      {/* ── Audit Log ── */}
      {tab === "audit" && <AuditLogPanel />}
    </div>
  );
}

// ── Generate Module Panel ─────────────────────────────────────────────────────

function GenerateModulePanel({ showToast }: { showToast: (msg: string, type?: "ok" | "err") => void }) {
  const [specialty, setSpecialty] = useState("");
  const [topic, setTopic]         = useState("");
  const [level, setLevel]         = useState(2);
  const [autoPublish, setAutoPublish] = useState(false);
  const [loading, setLoading]     = useState(false);
  const [result, setResult]       = useState<any>(null);

  // Import file
  const fileRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);

  const generate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!specialty.trim() || !topic.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await adminApi.generateModule({ specialty, topic, level, auto_publish: autoPublish });
      setResult(res);
      showToast(`Module ${res.code} generated!`);
    } catch (err: any) {
      showToast(err.response?.data?.detail ?? "Generation failed", "err");
    } finally {
      setLoading(false);
    }
  };

  const importFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      const res = await adminApi.importModule(file, autoPublish);
      showToast(`Imported ${res.code} — ${res.lessons} lessons, ${res.flashcards} cards`);
      setResult(res);
    } catch (err: any) {
      showToast(err.response?.data?.detail ?? "Import failed", "err");
    } finally {
      setImporting(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <div className="max-w-xl space-y-6">
      {/* Generate via AI */}
      <div className="card p-6">
        <h2 className="font-syne font-bold text-base text-ink mb-4">✨ Generate Module via Claude AI</h2>
        <form onSubmit={generate} className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-ink-3 mb-1 block">Specialty</label>
            <input
              value={specialty}
              onChange={e => setSpecialty(e.target.value)}
              placeholder="e.g. Cardiology"
              className="input w-full"
              required
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-ink-3 mb-1 block">Topic</label>
            <input
              value={topic}
              onChange={e => setTopic(e.target.value)}
              placeholder="e.g. Atrial Fibrillation"
              className="input w-full"
              required
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-ink-3 mb-1 block">Level (1–5)</label>
            <input
              type="range" min={1} max={5} value={level}
              onChange={e => setLevel(Number(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-ink-3 mt-0.5">
              <span>1 Beginner</span><span>3 Advanced</span><span>5 Expert</span>
            </div>
            <div className="text-center text-sm font-semibold text-accent mt-1">Level {level}</div>
          </div>
          <label className="flex items-center gap-2 text-sm text-ink cursor-pointer">
            <input type="checkbox" checked={autoPublish} onChange={e => setAutoPublish(e.target.checked)} />
            Auto-publish after generation
          </label>
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? "Generating… (may take 30s)" : "Generate Module"}
          </button>
        </form>
      </div>

      {/* Import JSON */}
      <div className="card p-6">
        <h2 className="font-syne font-bold text-base text-ink mb-2">📂 Import from JSON file</h2>
        <p className="text-xs text-ink-3 mb-4">Upload a module_*.json file in the standard MedMind format.</p>
        <input
          ref={fileRef}
          type="file"
          accept=".json"
          onChange={importFile}
          className="hidden"
        />
        <button
          onClick={() => fileRef.current?.click()}
          disabled={importing}
          className="btn-primary w-full"
        >
          {importing ? "Importing…" : "Choose JSON file"}
        </button>
      </div>

      {/* Result preview */}
      {result && (
        <div className="card p-4 border border-green-200 dark:border-green-800">
          <div className="font-syne font-bold text-sm text-green-700 dark:text-green-400 mb-2">
            ✓ {result.code} — {result.title}
          </div>
          <div className="grid grid-cols-4 gap-2 text-center">
            {[
              ["Lessons", result.lessons],
              ["Flashcards", result.flashcards],
              ["MCQ", result.mcq],
              ["Cases", result.cases],
            ].map(([label, val]) => (
              <div key={label} className="bg-surface-2 rounded-lg p-2">
                <div className="font-bold text-lg text-ink">{val}</div>
                <div className="text-xs text-ink-3">{label}</div>
              </div>
            ))}
          </div>
          <div className="mt-2 text-xs text-ink-3">
            Published: {result.is_published ? "Yes" : "No (draft)"}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Articles Panel ────────────────────────────────────────────────────────────

const ARTICLE_CATEGORIES = [
  "diseases", "drugs", "procedures", "symptoms", "diagnostics",
  "emergency", "nutrition", "pediatrics", "cardiology", "neurology",
  "oncology", "surgery", "psychiatry", "endocrinology", "infectious-diseases", "veterinary",
];
const SCHEMA_TYPES = ["MedicalCondition", "Drug", "MedicalProcedure", "MedicalWebPage"];
const ARTICLE_CATEGORY_LABELS: Record<string, string> = {
  diseases: "Diseases", drugs: "Drugs", procedures: "Procedures", symptoms: "Symptoms",
  diagnostics: "Diagnostics", emergency: "Emergency", nutrition: "Nutrition", pediatrics: "Pediatrics",
  cardiology: "Cardiology", neurology: "Neurology", oncology: "Oncology", surgery: "Surgery",
  psychiatry: "Psychiatry", endocrinology: "Endocrinology", "infectious-diseases": "Infectious Diseases", veterinary: "Veterinary",
};

type AdminArticle = {
  id: string; slug: string; title: string; category: string;
  reading_time_minutes: number; is_published: boolean; generated_by?: string;
  published_at: string | null; review_status?: string;
  author?: { name: string; is_ai: boolean } | null;
};

type PendingArticle = {
  id: string; slug: string; title: string; category: string;
  excerpt: string; author_name: string; submitted_at: string | null;
  body?: object[]; previewOpen?: boolean;
};

type ArticleSubTab = "all" | "pending";

function ArticlesPanel({ showToast }: { showToast: (msg: string, type?: "ok" | "err") => void }) {
  const [subTab, setSubTab] = useState<ArticleSubTab>("all");
  const [articles, setArticles] = useState<AdminArticle[]>([]);
  const [total, setTotal] = useState(0);
  const [pending, setPending] = useState<PendingArticle[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [filterPublished, setFilterPublished] = useState<"" | "true" | "false">("");
  const [filterReviewStatus, setFilterReviewStatus] = useState<string>("");
  const [reviewNote, setReviewNote] = useState<Record<string, string>>({});
  const [actioning, setActioning] = useState<string | null>(null);
  const [loadingPreview, setLoadingPreview] = useState<string | null>(null);

  // Generate form
  const [topic, setTopic] = useState("");
  const [category, setCategory] = useState("diseases");
  const [schemaType, setSchemaType] = useState("MedicalCondition");
  const [genModel, setGenModel] = useState<"haiku" | "sonnet" | "ollama">("haiku");
  const [autoPublish, setAutoPublish] = useState(false);
  const [showGenForm, setShowGenForm] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = { page: 1, limit: 100 };
      if (filterPublished !== "") params.published = filterPublished === "true";
      if (filterReviewStatus !== "") params.review_status = filterReviewStatus;
      const r = await api.get("/articles/admin/list", { params });
      setArticles(r.data.articles ?? []);
      setTotal(r.data.total ?? 0);
    } catch {
      showToast("Failed to load articles", "err");
    } finally {
      setLoading(false);
    }
  }, [filterPublished, filterReviewStatus]);

  const loadPending = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get("/articles/admin/pending");
      const list = Array.isArray(r.data) ? r.data : (r.data.articles ?? []);
      setPending(list.map((a: any) => ({
        ...a,
        author_name: a.author?.name ?? "Unknown",
        previewOpen: false,
      })));
    } catch {
      showToast("Failed to load pending articles", "err");
    } finally {
      setLoading(false);
    }
  }, []);

  // Load pending count immediately on mount (for badge)
  useEffect(() => { loadPending(); }, [loadPending]);

  useEffect(() => {
    if (subTab === "all") load();
    if (subTab === "pending") loadPending();
  }, [subTab, load, loadPending]);

  const togglePreview = async (id: string) => {
    const article = pending.find(a => a.id === id);
    if (!article) return;
    if (article.body !== undefined) {
      // already loaded — just toggle
      setPending(prev => prev.map(a => a.id === id ? { ...a, previewOpen: !a.previewOpen } : a));
      return;
    }
    setLoadingPreview(id);
    try {
      const r = await api.get(`/articles/admin/${id}`);
      setPending(prev => prev.map(a => a.id === id ? { ...a, body: r.data.body ?? [], previewOpen: true } : a));
    } catch {
      showToast("Failed to load article preview", "err");
    } finally {
      setLoadingPreview(null);
    }
  };

  const approveArticle = async (id: string) => {
    setActioning(id);
    try {
      await api.patch(`/articles/${id}/approve`);
      setPending(prev => prev.filter(a => a.id !== id));
      showToast("Article approved and published");
    } catch {
      showToast("Approve failed", "err");
    } finally {
      setActioning(null);
    }
  };

  const rejectArticle = async (id: string) => {
    setActioning(id);
    try {
      await api.patch(`/articles/${id}/reject`, null, { params: { note: reviewNote[id] ?? "" } });
      setPending(prev => prev.filter(a => a.id !== id));
      showToast("Article rejected");
    } catch {
      showToast("Reject failed", "err");
    } finally {
      setActioning(null);
    }
  };

  const generate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;
    setGenerating(true);
    try {
      const r = await api.post("/articles/generate", {
        topic, category, schema_type: schemaType, model: genModel, auto_publish: autoPublish,
      });
      showToast(`Generated: "${r.data.title}"`);
      setTopic("");
      setShowGenForm(false);
      load();
    } catch (err: any) {
      showToast(err.response?.data?.detail ?? "Generation failed", "err");
    } finally {
      setGenerating(false);
    }
  };

  const togglePublish = async (a: AdminArticle) => {
    try {
      await api.patch(`/articles/${a.id}/publish`, null, { params: { publish: !a.is_published } });
      setArticles(prev => prev.map(x => x.id === a.id ? { ...x, is_published: !a.is_published } : x));
      showToast(a.is_published ? "Unpublished" : "Published");
    } catch {
      showToast("Update failed", "err");
    }
  };

  const deleteArticle = async (a: AdminArticle) => {
    if (!confirm(`Delete "${a.title}"?`)) return;
    try {
      await api.delete(`/articles/${a.id}`);
      setArticles(prev => prev.filter(x => x.id !== a.id));
      showToast("Article deleted");
    } catch {
      showToast("Delete failed", "err");
    }
  };

  return (
    <div className="space-y-5">
      {/* Sub-tabs */}
      <div className="flex gap-1 bg-surface border border-border rounded-lg p-1 w-fit">
        <button
          onClick={() => setSubTab("all")}
          className={`font-syne font-semibold text-sm px-4 py-1.5 rounded transition-colors ${subTab === "all" ? "bg-ink text-white" : "text-ink-2 hover:text-ink"}`}
        >
          All Articles
        </button>
        <button
          onClick={() => setSubTab("pending")}
          className={`font-syne font-semibold text-sm px-4 py-1.5 rounded transition-colors flex items-center gap-1.5 ${subTab === "pending" ? "bg-ink text-white" : "text-ink-2 hover:text-ink"}`}
        >
          Pending Review
          {pending.length > 0 && (
            <span className={`text-[10px] rounded-full px-1.5 py-0.5 font-bold ${subTab === "pending" ? "bg-white text-ink" : "bg-amber text-white"}`}>
              {pending.length}
            </span>
          )}
        </button>
      </div>

      {/* ── Pending Review ── */}
      {subTab === "pending" && (
        <div className="space-y-4">
          {loading ? (
            <div className="text-center py-10 text-ink-3 text-sm">Loading…</div>
          ) : pending.length === 0 ? (
            <div className="text-center py-10 text-ink-3 font-serif text-sm">No articles awaiting review</div>
          ) : (
            pending.map(a => (
              <div key={a.id} className="card p-5">
                <div className="flex items-start gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-syne font-semibold text-amber bg-amber-light border border-amber/20 rounded-full px-2.5 py-0.5">
                        Pending Review
                      </span>
                      <span className="text-xs text-ink-3 font-syne capitalize">{a.category}</span>
                    </div>
                    <h3 className="font-syne font-bold text-base text-ink mb-1">{a.title}</h3>
                    <p className="font-serif text-sm text-ink-3 line-clamp-2">{a.excerpt}</p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-ink-3 font-serif">
                      <span>By <strong className="text-ink-2">{a.author_name}</strong></span>
                      {a.submitted_at && (
                        <span>· Submitted {new Date(a.submitted_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-col gap-1.5 flex-shrink-0">
                    <button
                      onClick={() => togglePreview(a.id)}
                      disabled={loadingPreview === a.id}
                      className="text-xs font-syne border border-border rounded px-3 py-1.5 text-ink-3 hover:text-ink text-center transition-colors"
                    >
                      {loadingPreview === a.id ? "…" : a.previewOpen ? "Hide" : "Preview"}
                    </button>
                    <button
                      onClick={() => approveArticle(a.id)}
                      disabled={actioning === a.id}
                      className="text-xs font-syne font-semibold border border-green/30 text-green bg-green-light hover:bg-green hover:text-white rounded px-3 py-1.5 transition-colors"
                    >
                      {actioning === a.id ? "…" : "✓ Approve"}
                    </button>
                    <button
                      onClick={() => rejectArticle(a.id)}
                      disabled={actioning === a.id}
                      className="text-xs font-syne font-semibold border border-red/30 text-red hover:bg-red-light rounded px-3 py-1.5 transition-colors"
                    >
                      {actioning === a.id ? "…" : "✕ Reject"}
                    </button>
                  </div>
                </div>

                {/* Inline body preview */}
                {a.previewOpen && a.body && (
                  <div className="mt-3 pt-3 border-t border-border bg-surface-2 rounded-lg p-4 space-y-2 max-h-96 overflow-y-auto">
                    {(a.body as any[]).length === 0 ? (
                      <p className="text-xs text-ink-3 font-serif italic">No content blocks yet.</p>
                    ) : (a.body as any[]).map((block: any, i: number) => (
                      <div key={i}>
                        {block.type === "h2" && <h2 className="font-syne font-bold text-base text-ink">{block.content}</h2>}
                        {block.type === "h3" && <h3 className="font-syne font-semibold text-sm text-ink">{block.content}</h3>}
                        {block.type === "p" && <p className="font-serif text-sm text-ink-2 leading-relaxed">{block.content}</p>}
                        {block.type === "ul" && (
                          <ul className="list-disc list-inside font-serif text-sm text-ink-2 space-y-0.5">
                            {(block.items ?? []).map((item: string, j: number) => <li key={j}>{item}</li>)}
                          </ul>
                        )}
                        {block.type === "callout" && (
                          <div className={`border rounded-lg px-3 py-2 text-xs font-serif ${block.variant === "warning" ? "border-amber/30 bg-amber-light text-amber" : block.variant === "tip" ? "border-green/30 bg-green-light text-green" : "border-blue/30 bg-blue-light text-blue"}`}>
                            {block.content}
                          </div>
                        )}
                        {block.type === "image" && block.url && (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={block.url} alt={block.alt ?? ""} className="max-h-32 rounded border border-border object-contain" />
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Rejection note */}
                <div className="mt-3 pt-3 border-t border-border">
                  <input
                    value={reviewNote[a.id] ?? ""}
                    onChange={e => setReviewNote(prev => ({ ...prev, [a.id]: e.target.value }))}
                    placeholder="Optional rejection note shown to the author…"
                    className="input w-full text-sm"
                  />
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* ── All Articles ── */}
      {subTab === "all" && <>
      {/* Toolbar */}
      <div className="flex gap-2 flex-wrap items-center">
        <select
          value={filterPublished}
          onChange={e => setFilterPublished(e.target.value as "" | "true" | "false")}
          className="border border-border rounded px-3 py-1.5 text-sm font-serif bg-bg focus:outline-none"
        >
          <option value="">All visibility</option>
          <option value="true">Published</option>
          <option value="false">Hidden</option>
        </select>
        <select
          value={filterReviewStatus}
          onChange={e => setFilterReviewStatus(e.target.value)}
          className="border border-border rounded px-3 py-1.5 text-sm font-serif bg-bg focus:outline-none"
        >
          <option value="">All review status</option>
          <option value="published">Approved</option>
          <option value="pending_review">Pending Review</option>
          <option value="draft">Draft</option>
          <option value="rejected">Rejected</option>
        </select>
        <button onClick={load} className="btn-primary text-xs">Refresh</button>
        <div className="ml-auto">
          <button
            onClick={() => setShowGenForm(v => !v)}
            className="font-syne font-semibold text-sm bg-ink text-white rounded-lg px-4 py-1.5 hover:bg-ink-2 transition-colors"
          >
            {showGenForm ? "✕ Cancel" : "✨ Generate Article"}
          </button>
        </div>
      </div>

      {/* Generate form */}
      {showGenForm && (
        <div className="card p-5 border-2 border-ink/10">
          <h3 className="font-syne font-bold text-sm text-ink mb-4">Generate Medical Article via Claude AI</h3>
          <form onSubmit={generate} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label className="text-xs font-semibold text-ink-3 mb-1 block">Topic *</label>
              <input
                value={topic}
                onChange={e => setTopic(e.target.value)}
                placeholder="e.g. Atrial Fibrillation, Metformin, Appendectomy..."
                className="input w-full"
                required
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-ink-3 mb-1 block">Category</label>
              <select value={category} onChange={e => setCategory(e.target.value)} className="input w-full">
                {ARTICLE_CATEGORIES.map(c => (
                  <option key={c} value={c}>{ARTICLE_CATEGORY_LABELS[c] ?? c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-ink-3 mb-1 block">Schema type</label>
              <select value={schemaType} onChange={e => setSchemaType(e.target.value)} className="input w-full">
                {SCHEMA_TYPES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-ink-3 mb-1 block">Model</label>
              <select value={genModel} onChange={e => setGenModel(e.target.value as "haiku" | "sonnet" | "ollama")} className="input w-full">
                <option value="ollama">Ollama / Qwen (free, local)</option>
                <option value="haiku">Claude Haiku (fast, ~$0.01)</option>
                <option value="sonnet">Claude Sonnet (quality, ~$0.10)</option>
              </select>
            </div>
            <div className="flex items-center gap-2 self-end pb-0.5">
              <input
                type="checkbox"
                id="art-autopub"
                checked={autoPublish}
                onChange={e => setAutoPublish(e.target.checked)}
              />
              <label htmlFor="art-autopub" className="text-sm font-serif text-ink cursor-pointer">Auto-publish</label>
            </div>
            <div className="md:col-span-2">
              <button type="submit" disabled={generating} className="btn-primary w-full">
                {generating ? "Generating… (15–30s)" : "Generate Article"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Stats */}
      <div className="text-xs text-ink-3 font-serif">
        {total} articles — {articles.filter(a => a.is_published).length} published
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-ink-3 text-sm">Loading…</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-surface-2">
                  {["Title", "Category", "Author", "Read time", "Status", "Actions"].map(h => (
                    <th key={h} className="text-left px-4 py-2.5 font-syne font-semibold text-ink-2 text-xs uppercase">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {articles.map(a => (
                  <tr key={a.id} className="border-b border-border last:border-0 hover:bg-surface-2 transition-colors">
                    <td className="px-4 py-2.5">
                      <div className="font-syne font-semibold text-ink text-sm">{a.title}</div>
                      <div className="text-ink-3 text-xs font-mono">{a.slug}</div>
                    </td>
                    <td className="px-4 py-2.5 text-ink-2 font-serif text-xs capitalize">
                      {ARTICLE_CATEGORY_LABELS[a.category] ?? a.category}
                    </td>
                    <td className="px-4 py-2.5 text-xs">
                      {a.author?.is_ai === false ? (
                        <span className="font-syne font-semibold text-ink">{a.author.name}</span>
                      ) : (
                        <span className="font-mono text-ink-3">{a.generated_by ?? "ai"}</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-ink-3 text-xs">{a.reading_time_minutes}m</td>
                    <td className="px-4 py-2.5">
                      <div className="flex flex-col gap-1">
                        <button
                          onClick={() => togglePublish(a)}
                          className={`font-syne font-semibold text-xs border rounded px-2.5 py-0.5 transition-colors ${
                            a.is_published
                              ? "border-green/30 text-green bg-green-light hover:bg-green hover:text-white"
                              : "border-border text-ink-3 hover:border-ink hover:text-ink"
                          }`}
                        >
                          {a.is_published ? "✓ Published" : "Hidden"}
                        </button>
                        {a.review_status && a.review_status !== "published" && (
                          <span className={`text-[10px] font-syne font-semibold rounded px-1.5 py-0.5 w-fit ${
                            a.review_status === "pending_review" ? "bg-amber-light text-amber" :
                            a.review_status === "rejected"       ? "bg-red-light text-red" :
                            "bg-surface-2 text-ink-3"
                          }`}>
                            {a.review_status === "pending_review" ? "Pending" :
                             a.review_status === "rejected"       ? "Rejected" :
                             a.review_status}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-2.5 flex gap-2">
                      <a
                        href={`/articles/${a.slug}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs font-syne text-ink-3 hover:text-ink border border-border rounded px-2 py-0.5"
                      >
                        View
                      </a>
                      <button
                        onClick={() => deleteArticle(a)}
                        className="text-xs font-syne text-red hover:bg-red-light border border-red/30 rounded px-2 py-0.5"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
                {!articles.length && !loading && (
                  <tr><td colSpan={6} className="px-4 py-10 text-center text-ink-3 font-serif text-sm">
                    No articles yet. Generate your first one above.
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
      </>}
    </div>
  );
}


// ── Translations Panel ────────────────────────────────────────────────────────

const LOCALE_LABELS: Record<string, string> = {
  ru: "Русский", ar: "العربية", tr: "Türkçe", de: "Deutsch", fr: "Français", es: "Español",
};

function TranslationsPanel({ showToast }: { showToast: (msg: string, type?: "ok" | "err") => void }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [retrying, setRetrying] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get("/admin/translations/stats");
      setData(r.data);
    } catch {
      showToast("Failed to load translation stats", "err");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const retranslateAll = async (locale?: string) => {
    const key = locale ?? "all";
    setRetrying(key);
    try {
      const r = await api.post("/admin/translations/retranslate-failed", null, {
        params: locale ? { locale } : {},
      });
      showToast(`Queued ${r.data.queued} lessons for retranslation`);
      setTimeout(load, 1000);
    } catch {
      showToast("Failed to queue retranslation", "err");
    } finally {
      setRetrying(null);
    }
  };

  if (loading) return <div className="text-center py-10 text-ink-3">Loading…</div>;
  if (!data) return null;

  const totalFailed = data.locales.reduce((s: number, l: any) => s + l.failed, 0);

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Summary */}
      <div className="card p-4 flex items-center gap-4 flex-wrap">
        <div>
          <div className="font-syne font-black text-2xl text-ink">{data.total_published_lessons}</div>
          <div className="text-xs text-ink-3 font-syne">Published lessons</div>
        </div>
        <div className="flex-1" />
        {totalFailed > 0 && (
          <button
            onClick={() => retranslateAll()}
            disabled={retrying !== null}
            className="text-xs font-syne font-semibold border border-red/30 text-red hover:bg-red-light rounded px-3 py-1.5 transition-colors"
          >
            {retrying === "all" ? "Queuing…" : `Retry all failed (${totalFailed})`}
          </button>
        )}
        <button onClick={load} className="btn-primary text-xs">Refresh</button>
      </div>

      {/* Per-locale table */}
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-surface-2 border-b border-border">
            <tr>
              {["Locale", "Done", "Pending", "In Progress", "Failed", "Coverage", ""].map(h => (
                <th key={h} className="text-left px-4 py-2.5 font-syne font-semibold text-ink-2 text-xs uppercase">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.locales.map((l: any) => (
              <tr key={l.locale} className="border-b border-border last:border-0 hover:bg-surface-2">
                <td className="px-4 py-2.5 font-syne font-semibold text-ink text-sm">
                  {l.locale.toUpperCase()} <span className="text-ink-3 font-normal text-xs ml-1">{LOCALE_LABELS[l.locale]}</span>
                </td>
                <td className="px-4 py-2.5 text-green font-syne font-semibold text-sm">{l.done}</td>
                <td className="px-4 py-2.5 text-ink-3 text-sm">{l.pending}</td>
                <td className="px-4 py-2.5 text-amber font-syne text-sm">{l.translating}</td>
                <td className="px-4 py-2.5">
                  {l.failed > 0 ? (
                    <span className="text-red font-syne font-semibold text-sm">{l.failed}</span>
                  ) : (
                    <span className="text-ink-3 text-sm">0</span>
                  )}
                </td>
                <td className="px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    <div className="w-24 h-1.5 bg-surface-2 border border-border rounded-full overflow-hidden">
                      <div
                        className="h-full bg-green rounded-full transition-all"
                        style={{ width: `${l.coverage_pct}%` }}
                      />
                    </div>
                    <span className="text-xs text-ink-3 font-syne">{l.coverage_pct}%</span>
                  </div>
                </td>
                <td className="px-4 py-2.5">
                  {l.failed > 0 && (
                    <button
                      onClick={() => retranslateAll(l.locale)}
                      disabled={retrying !== null}
                      className="text-[11px] font-syne font-semibold border border-red/30 text-red hover:bg-red-light rounded px-2 py-0.5 transition-colors"
                    >
                      {retrying === l.locale ? "…" : "Retry failed"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Recent failures */}
      {data.recent_failures.length > 0 && (
        <div>
          <h3 className="font-syne font-bold text-sm text-ink-2 uppercase tracking-wider mb-3">Recent Failures</h3>
          <div className="card overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-surface-2 border-b border-border">
                <tr>
                  {["Lesson", "Locale", "Error"].map(h => (
                    <th key={h} className="text-left px-4 py-2 font-syne font-semibold text-ink-2 uppercase">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.recent_failures.map((f: any, i: number) => (
                  <tr key={i} className="border-t border-border hover:bg-surface-2">
                    <td className="px-4 py-2 text-ink font-semibold">{f.lesson_title}</td>
                    <td className="px-4 py-2 text-ink-3">{f.locale.toUpperCase()}</td>
                    <td className="px-4 py-2 text-red font-mono text-[10px] max-w-xs truncate">{f.error ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}


// ── Feature Flags Panel ───────────────────────────────────────────────────────

const FLAG_DESCRIPTIONS: Record<string, string> = {
  pgvector_search:   "Semantic vector search (requires pgvector extension)",
  ai_memory:         "Long-term AI memory extraction per user",
  pdf_export:        "CPD/CME certificate PDF export",
  ugc_flashcards:    "User-generated flashcards",
  posthog_analytics: "PostHog usage analytics",
  sentry_monitoring: "Sentry error reporting",
  imaging_library:   "Medical imaging library (X-ray, MRI, CT)",
  anatomy_3d:        "3D anatomy viewer",
};

function FeatureFlagsPanel({ showToast }: { showToast: (msg: string, type?: "ok" | "err") => void }) {
  const [flags, setFlags] = useState<Record<string, { enabled: boolean; rollout: number; source: string }>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);

  const load = async () => {
    try {
      const r = await api.get("/admin/feature-flags");
      setFlags(r.data);
    } catch {
      showToast("Failed to load feature flags", "err");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const toggle = async (flag: string, enabled: boolean) => {
    setSaving(flag);
    try {
      const rollout = flags[flag]?.rollout ?? 100;
      await api.patch(`/admin/feature-flags/${flag}`, null, {
        params: { enabled, rollout },
      });
      setFlags(prev => ({ ...prev, [flag]: { ...prev[flag], enabled, source: "redis" } }));
      showToast(`${flag} ${enabled ? "enabled" : "disabled"}`);
    } catch {
      showToast("Failed to update flag", "err");
    } finally {
      setSaving(null);
    }
  };

  const setRollout = async (flag: string, rollout: number) => {
    setSaving(flag);
    try {
      await api.patch(`/admin/feature-flags/${flag}`, null, {
        params: { enabled: flags[flag]?.enabled ?? false, rollout },
      });
      setFlags(prev => ({ ...prev, [flag]: { ...prev[flag], rollout, source: "redis" } }));
      showToast(`${flag} rollout → ${rollout}%`);
    } catch {
      showToast("Failed to update rollout", "err");
    } finally {
      setSaving(null);
    }
  };

  if (loading) return <div className="text-center py-10 text-ink-3">Loading…</div>;

  return (
    <div className="max-w-2xl space-y-3">
      <p className="text-xs text-ink-3 font-serif mb-4">
        Feature flags control optional platform features in real-time without a redeploy. Values are stored in Redis.
      </p>
      {Object.entries(flags).map(([flag, val]) => (
        <div key={flag} className="card p-4">
          <div className="flex items-start gap-4">
            <div className="flex-1">
              <div className="font-syne font-semibold text-sm text-ink">{flag.replace(/_/g, " ")}</div>
              <div className="text-xs text-ink-3 mt-0.5">{FLAG_DESCRIPTIONS[flag] ?? ""}</div>
              <div className="text-[10px] text-ink-3 mt-1 font-mono">source: {val.source}</div>
            </div>

            {/* Toggle */}
            <button
              onClick={() => toggle(flag, !val.enabled)}
              disabled={saving === flag}
              className={`relative w-11 h-6 rounded-full border-2 transition-colors focus:outline-none ${
                val.enabled
                  ? "bg-green border-green"
                  : "bg-surface-2 border-border"
              }`}
            >
              <span
                className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${
                  val.enabled ? "translate-x-5" : "translate-x-0"
                }`}
              />
            </button>
          </div>

          {/* Rollout slider — only relevant when enabled */}
          {val.enabled && (
            <div className="mt-3 flex items-center gap-3">
              <span className="text-xs text-ink-3 font-syne w-16">Rollout</span>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                value={val.rollout}
                onChange={(e) => setFlags(prev => ({
                  ...prev,
                  [flag]: { ...prev[flag], rollout: Number(e.target.value) },
                }))}
                onMouseUp={(e) => setRollout(flag, Number((e.target as HTMLInputElement).value))}
                className="flex-1"
              />
              <span className="text-xs font-syne font-bold text-ink w-10 text-right">{val.rollout}%</span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}


// ── System Health Panel ───────────────────────────────────────────────────────

function SystemHealthPanel() {
  const [health, setHealth] = useState<Record<string, any> | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get("/admin/system/health");
      setHealth(r.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const statusColor = (val: any) => {
    if (val === "ok" || val === "configured") return "text-green";
    if (typeof val === "object" && val?.status === "ok") return "text-green";
    if (val === "not configured") return "text-ink-3";
    return "text-red";
  };

  const statusText = (val: any): string => {
    if (typeof val === "string") return val;
    if (typeof val === "object" && val !== null) {
      if (val.status === "ok") {
        const extras = Object.entries(val)
          .filter(([k]) => k !== "status")
          .map(([k, v]) => `${k}: ${v}`)
          .join(" · ");
        return `ok${extras ? " — " + extras : ""}`;
      }
      return val.status ?? JSON.stringify(val);
    }
    return String(val);
  };

  if (loading) return <div className="text-center py-10 text-ink-3">Loading…</div>;
  if (!health) return null;

  const AI_KEYS = ["anthropic", "gemini", "groq"];
  const SERVICES = Object.entries(health).filter(([k]) => !AI_KEYS.includes(k));
  const AI = Object.entries(health).filter(([k]) => AI_KEYS.includes(k));

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex justify-end">
        <button onClick={load} className="btn-primary text-xs">Refresh</button>
      </div>

      {/* Core services */}
      <section>
        <h3 className="font-syne font-bold text-xs text-ink-2 uppercase tracking-wider mb-3">Core Services</h3>
        <div className="card divide-y divide-border">
          {SERVICES.map(([key, val]) => (
            <div key={key} className="px-4 py-3 flex items-start gap-4">
              <span className="font-syne font-semibold text-sm text-ink w-28 capitalize">{key.replace(/_/g, " ")}</span>
              <span className={`font-mono text-xs flex-1 ${statusColor(val)}`}>{statusText(val)}</span>
            </div>
          ))}
        </div>
      </section>

      {/* AI providers */}
      <section>
        <h3 className="font-syne font-bold text-xs text-ink-2 uppercase tracking-wider mb-3">AI Providers</h3>
        <div className="card divide-y divide-border">
          {AI.map(([key, val]) => (
            <div key={key} className="px-4 py-3 flex items-start gap-4">
              <span className="font-syne font-semibold text-sm text-ink w-28 capitalize">{key}</span>
              <span className={`font-mono text-xs ${statusColor(val)}`}>{statusText(val)}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}


// ── Audit Log Panel ───────────────────────────────────────────────────────────

type AuditEntry = {
  id: string;
  user_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  ip_address: string | null;
  created_at: string;
};

function AuditLogPanel() {
  const [logs, setLogs]         = useState<AuditEntry[]>([]);
  const [total, setTotal]       = useState(0);
  const [page, setPage]         = useState(1);
  const [action, setAction]     = useState("");
  const [userId, setUserId]     = useState("");
  const [loading, setLoading]   = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = { page, limit: 50 };
      if (action) params.action = action;
      if (userId) params.user_id = userId;
      const res = await adminApi.getAuditLogs(params);
      setLogs(res.logs ?? []);
      setTotal(res.total ?? 0);
    } catch {
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, [page, action, userId]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex gap-3 flex-wrap">
        <input
          value={action}
          onChange={e => { setAction(e.target.value); setPage(1); }}
          placeholder="Filter by action…"
          className="input w-48"
        />
        <input
          value={userId}
          onChange={e => { setUserId(e.target.value); setPage(1); }}
          placeholder="Filter by user ID…"
          className="input w-64 font-mono text-xs"
        />
        <button onClick={load} className="btn-primary px-4">Refresh</button>
      </div>

      <div className="text-xs text-ink-3">{total} entries</div>

      {loading ? (
        <div className="text-center py-8 text-ink-3">Loading…</div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-xs">
            <thead className="bg-surface-2">
              <tr>
                {["Time", "Action", "Resource", "User ID", "IP"].map(h => (
                  <th key={h} className="text-left px-3 py-2 font-semibold text-ink-3">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {logs.map(log => (
                <tr key={log.id} className="border-t border-border hover:bg-surface-2">
                  <td className="px-3 py-2 text-ink-3 whitespace-nowrap">
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                  <td className="px-3 py-2 font-mono text-accent">{log.action}</td>
                  <td className="px-3 py-2 text-ink-3">
                    {log.resource_type}{log.resource_id ? ` / ${log.resource_id.slice(0, 8)}…` : ""}
                  </td>
                  <td className="px-3 py-2 font-mono text-ink-3">
                    {log.user_id ? log.user_id.slice(0, 8) + "…" : "—"}
                  </td>
                  <td className="px-3 py-2 text-ink-3">{log.ip_address ?? "—"}</td>
                </tr>
              ))}
              {logs.length === 0 && (
                <tr><td colSpan={5} className="px-3 py-8 text-center text-ink-3">No entries</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {total > 50 && (
        <div className="flex gap-2 justify-end">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="btn text-xs px-3">← Prev</button>
          <span className="text-xs text-ink-3 self-center">Page {page}</span>
          <button onClick={() => setPage(p => p + 1)} disabled={page * 50 >= total} className="btn text-xs px-3">Next →</button>
        </div>
      )}
    </div>
  );
}
