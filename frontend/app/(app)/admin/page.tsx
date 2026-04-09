"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { api, adminApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

type Stats = {
  users: { total: number; active: number; new_last_7_days: number; by_tier: Record<string, number> };
  content: { modules_total: number; modules_published: number; lessons: number; flashcards: number; mcq: number; cases: number };
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

type Tab = "overview" | "users" | "modules" | "generate" | "audit";

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
          ["overview", "📊 Overview"],
          ["users",    "👥 Users"],
          ["modules",  "📚 Modules"],
          ["generate", "✨ Generate"],
          ["audit",    "🔍 Audit Log"],
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
