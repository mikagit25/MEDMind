"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
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

type Tab = "overview" | "users" | "modules";

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
      <div className="flex gap-1 mb-6 bg-surface border border-border rounded-lg p-1 w-fit">
        {(["overview", "users", "modules"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`font-syne font-semibold text-sm px-4 py-1.5 rounded capitalize transition-colors ${
              tab === t ? "bg-ink text-white" : "text-ink-2 hover:text-ink"
            }`}
          >
            {t === "overview" ? "📊 Overview" : t === "users" ? "👥 Users" : "📚 Modules"}
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
    </div>
  );
}
