"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { studentCoursesApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { useT } from "@/lib/i18n";

// ── Types ──────────────────────────────────────────────────────────────────────
type PublicCourse = {
  id: string;
  title: string;
  description?: string;
  teacher_name?: string;
  enrollment_type: "open" | "invite" | "request";
  difficulty?: string;
  specialty_tag?: string;
  thumbnail_emoji: string;
  estimated_hours?: number;
  module_count: number;
  student_count: number;
  is_public: boolean;
};

type EnrolledCourse = {
  id: string;
  title: string;
  description?: string;
  teacher_name?: string;
  specialty?: string;
  total_modules: number;
  overall_completion: number;
  enrolled_at: string;
};

type RequestStatus = "pending" | "approved" | "denied" | null;

type Tab = "enrolled" | "discover" | "join";

const DIFFICULTY_LABEL_KEY: Record<string, string> = {
  beginner: "courses.difficulty_beginner",
  intermediate: "courses.difficulty_intermediate",
  advanced: "courses.difficulty_advanced",
};
const DIFFICULTY_COLOR: Record<string, string> = {
  beginner:     "bg-green-light text-green",
  intermediate: "bg-blue-light text-blue",
  advanced:     "bg-amber-light text-amber",
};

// ── Course card for discover tab ───────────────────────────────────────────────
function DiscoverCard({
  course,
  isEnrolled,
  onEnroll,
}: {
  course: PublicCourse;
  isEnrolled: boolean;
  onEnroll: (id: string, type: PublicCourse["enrollment_type"]) => Promise<void>;
}) {
  const t = useT();
  const [status, setStatus] = useState<"idle" | "loading" | "requested">(
    isEnrolled ? "idle" : "idle"
  );
  const [reqStatus, setReqStatus] = useState<RequestStatus>(null);
  const [showRequestForm, setShowRequestForm] = useState(false);
  const [requestMsg, setRequestMsg] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleEnroll = async () => {
    if (isEnrolled || status === "loading") return;
    setStatus("loading");
    await onEnroll(course.id, course.enrollment_type);
    setStatus("idle");
  };

  const handleRequest = async () => {
    setSubmitting(true);
    try {
      const res = await studentCoursesApi.requestAccess(course.id, requestMsg);
      setReqStatus(res.status ?? "pending");
      setShowRequestForm(false);
    } catch {
      setReqStatus("pending");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card flex flex-col gap-3 p-4 hover:border-ink-3 transition-all">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="text-3xl flex-shrink-0 w-10 h-10 flex items-center justify-center bg-surface rounded-xl">
          {course.thumbnail_emoji}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5 mb-1">
            {course.specialty_tag && (
              <span className="font-syne text-[10px] font-semibold text-ink-3 uppercase tracking-wide">
                {course.specialty_tag}
              </span>
            )}
            {course.difficulty && (
              <span className={`badge text-[10px] ${DIFFICULTY_COLOR[course.difficulty] ?? "bg-surface-2 text-ink-3"}`}>
                {t(DIFFICULTY_LABEL_KEY[course.difficulty] as any) || course.difficulty}
              </span>
            )}
            {course.enrollment_type === "open" && (
              <span className="badge bg-green-light text-green text-[10px]">{t("courses.free_badge")}</span>
            )}
            {course.enrollment_type === "request" && (
              <span className="badge bg-amber-light text-amber text-[10px]">{t("courses.by_request_badge")}</span>
            )}
          </div>
          <h3 className="font-syne font-bold text-sm text-ink leading-snug line-clamp-2">
            {course.title}
          </h3>
          {course.teacher_name && (
            <p className="font-serif text-[11px] text-ink-3 mt-0.5">by {course.teacher_name}</p>
          )}
        </div>
      </div>

      {/* Description */}
      {course.description && (
        <p className="font-serif text-xs text-ink-3 line-clamp-2 leading-relaxed">
          {course.description}
        </p>
      )}

      {/* Stats */}
      <div className="flex items-center gap-3 text-[11px] font-syne text-ink-3">
        <span>📖 {course.module_count} modules</span>
        {course.estimated_hours && <span>⏱ {course.estimated_hours}h</span>}
        <span>👥 {course.student_count} enrolled</span>
      </div>

      {/* CTA */}
      <div className="border-t border-border pt-3">
        {isEnrolled ? (
          <Link
            href={`/courses/${course.id}`}
            className="btn-primary text-xs px-4 py-2 w-full text-center block"
          >
            {t("courses.continue_learning")}
          </Link>
        ) : course.enrollment_type === "open" ? (
          <button
            onClick={handleEnroll}
            disabled={status === "loading"}
            className="btn-primary text-xs px-4 py-2 w-full disabled:opacity-50"
          >
            {status === "loading" ? t("courses.enrolling") : t("courses.enroll_free")}
          </button>
        ) : reqStatus === "pending" ? (
          <div className="text-xs font-syne text-amber text-center py-1">
            ⏳ {t("courses.access_pending")}
          </div>
        ) : reqStatus === "approved" ? (
          <Link href={`/courses/${course.id}`} className="btn-primary text-xs px-4 py-2 w-full text-center block">
            {t("courses.access_granted")}
          </Link>
        ) : showRequestForm ? (
          <div className="space-y-2">
            <textarea
              value={requestMsg}
              onChange={e => setRequestMsg(e.target.value)}
              placeholder={t("courses.request_placeholder")}
              rows={2}
              className="w-full text-xs font-serif border border-border rounded-lg px-3 py-2 bg-bg text-ink focus:outline-none focus:border-ink resize-none"
            />
            <div className="flex gap-2">
              <button
                onClick={() => setShowRequestForm(false)}
                className="btn-secondary text-xs px-3 py-1.5 flex-1"
              >
                {t("courses.cancel")}
              </button>
              <button
                onClick={handleRequest}
                disabled={submitting}
                className="btn-primary text-xs px-3 py-1.5 flex-1 disabled:opacity-50"
              >
                {submitting ? t("courses.sending") : t("courses.send_request")}
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setShowRequestForm(true)}
            className="btn-secondary text-xs px-4 py-2 w-full"
          >
            {t("courses.request_access")}
          </button>
        )}
      </div>
    </div>
  );
}

// ── Enrolled course card ───────────────────────────────────────────────────────
function EnrolledCard({ course, onLeave }: { course: EnrolledCourse; onLeave: (id: string) => void }) {
  const t = useT();
  const pct = Math.round(course.overall_completion ?? 0);
  return (
    <div className="card flex flex-col gap-3 p-4 hover:border-ink-3 transition-all">
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          {course.specialty && (
            <span className="font-syne text-[10px] font-semibold text-ink-3 uppercase tracking-wide block mb-1">
              {course.specialty}
            </span>
          )}
          <h3 className="font-syne font-bold text-sm text-ink leading-snug line-clamp-2">
            {course.title}
          </h3>
          {course.teacher_name && (
            <p className="font-serif text-[11px] text-ink-3 mt-0.5">by {course.teacher_name}</p>
          )}
          {course.enrolled_at && (
            <p className="font-serif text-[10px] text-ink-3 mt-0.5">
              Enrolled {new Date(course.enrolled_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
            </p>
          )}
        </div>
        <div className="flex-shrink-0 text-right">
          <div className={`font-syne font-black text-lg leading-none ${pct >= 100 ? "text-green" : "text-ink"}`}>
            {pct}%
          </div>
          <div className="font-serif text-[10px] text-ink-3">{course.total_modules} modules</div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-border-2 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${pct >= 100 ? "bg-green" : "bg-gradient-to-r from-blue to-blue/60"}`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>

      <div className="flex items-center gap-2 border-t border-border pt-3">
        <Link
          href={`/courses/${course.id}`}
          className="btn-primary text-xs px-4 py-1.5 flex-1 text-center"
        >
          {pct >= 100 ? t("courses.review_arrow") : t("courses.continue_arrow")}
        </Link>
        <button
          onClick={() => onLeave(course.id)}
          className="text-xs font-syne text-ink-3 hover:text-red border border-border hover:border-red/30 rounded-lg px-3 py-1.5 transition-colors"
          title={t("courses.leave")}
        >
          {t("courses.leave")}
        </button>
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────
export default function MyCoursesPage() {
  const { user } = useAuthStore();
  const t = useT();

  const [tab, setTab] = useState<Tab>("discover");
  const [enrolled, setEnrolled] = useState<EnrolledCourse[]>([]);
  const [publicCourses, setPublicCourses] = useState<PublicCourse[]>([]);
  const [loading, setLoading] = useState(true);
  const [enrolledIds, setEnrolledIds] = useState<Set<string>>(new Set());

  // Filters
  const [filterSpecialty, setFilterSpecialty] = useState<string>("all");
  const [filterDifficulty, setFilterDifficulty] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Join form
  const [joinCode, setJoinCode] = useState("");
  const [joining, setJoining] = useState(false);
  const [joinMsg, setJoinMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Load data
  useEffect(() => {
    setLoading(true);
    Promise.all([
      studentCoursesApi.getEnrolled().catch(() => []),
      studentCoursesApi.discover().catch(() => []),
    ]).then(([enrolledData, publicData]) => {
      const enrList = Array.isArray(enrolledData) ? enrolledData : enrolledData?.courses ?? [];
      setEnrolled(enrList);
      setEnrolledIds(new Set(enrList.map((c: EnrolledCourse) => c.id)));
      setPublicCourses(Array.isArray(publicData) ? publicData : []);
      // If already enrolled in some courses, start on "My courses" tab
      if (enrList.length > 0) setTab("enrolled");
    }).finally(() => setLoading(false));
  }, []);

  const handleEnroll = useCallback(async (courseId: string, type: PublicCourse["enrollment_type"]) => {
    if (type !== "open") return;
    try {
      await studentCoursesApi.joinById(courseId);
      setEnrolledIds(prev => new Set([...prev, courseId]));
      // Refresh enrolled list
      const updated = await studentCoursesApi.getEnrolled().catch(() => []);
      const list = Array.isArray(updated) ? updated : updated?.courses ?? [];
      setEnrolled(list);
      setTab("enrolled");
    } catch (e: any) {
      console.error("Enroll error", e);
    }
  }, []);

  const handleLeave = useCallback(async (courseId: string) => {
    if (!confirm("Leave this course? Your progress will be saved.")) return;
    try {
      await studentCoursesApi.leave(courseId);
      setEnrolled(prev => prev.filter(c => c.id !== courseId));
      setEnrolledIds(prev => { const s = new Set(prev); s.delete(courseId); return s; });
    } catch { /* noop */ }
  }, []);

  const handleJoin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!joinCode.trim()) return;
    setJoining(true);
    setJoinMsg(null);
    try {
      const res = await studentCoursesApi.join(joinCode.trim().toUpperCase());
      setJoinMsg({ type: "success", text: `Joined "${res.title ?? "course"}" successfully!` });
      setJoinCode("");
      const updated = await studentCoursesApi.getEnrolled().catch(() => []);
      const list = Array.isArray(updated) ? updated : updated?.courses ?? [];
      setEnrolled(list);
      setEnrolledIds(new Set(list.map((c: EnrolledCourse) => c.id)));
      setTab("enrolled");
    } catch (e: any) {
      setJoinMsg({ type: "error", text: e?.response?.data?.detail ?? "Invalid invite code or already enrolled." });
    } finally {
      setJoining(false);
    }
  };

  // Filtered discover list
  const specialties = Array.from(new Set(publicCourses.map(c => c.specialty_tag).filter(Boolean))) as string[];
  const filteredPublic = publicCourses.filter(c => {
    if (filterSpecialty !== "all" && c.specialty_tag !== filterSpecialty) return false;
    if (filterDifficulty !== "all" && c.difficulty !== filterDifficulty) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      if (!c.title.toLowerCase().includes(q) && !(c.teacher_name ?? "").toLowerCase().includes(q) && !(c.description ?? "").toLowerCase().includes(q)) return false;
    }
    return true;
  });

  // ── Tabs ──
  const TABS: { id: Tab; label: string; count?: number }[] = [
    { id: "discover", label: t("courses.discover") || "Discover", count: publicCourses.length },
    { id: "enrolled", label: t("courses.my_courses") || "My courses", count: enrolled.length },
    { id: "join", label: t("courses.join_code") || "Join with code" },
  ];

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-5xl mx-auto px-3 sm:px-6 py-4 sm:py-6">

        {/* Header */}
        <div className="mb-5">
          <h1 className="font-syne font-black text-xl sm:text-2xl text-ink">{t("courses.title") || "Courses"}</h1>
          <p className="font-serif text-xs text-ink-3 mt-0.5">
            {enrolled.length > 0
              ? t("courses.enrolled_and_available").replace("{n}", String(enrolled.length)).replace("{m}", String(publicCourses.length))
              : t("courses.available_free").replace("{n}", String(publicCourses.length))}
          </p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-5 border-b border-border">
          {TABS.map(tab_ => (
            <button
              key={tab_.id}
              onClick={() => setTab(tab_.id)}
              className={`px-4 py-2 font-syne font-semibold text-sm border-b-2 transition-colors -mb-px ${
                tab === tab_.id
                  ? "border-ink text-ink"
                  : "border-transparent text-ink-3 hover:text-ink"
              }`}
            >
              {tab_.label}
              {tab_.count !== undefined && tab_.count > 0 && (
                <span className={`ml-1.5 text-[10px] rounded-full px-1.5 py-0.5 ${
                  tab === tab_.id ? "bg-ink text-white" : "bg-surface-2 text-ink-3"
                }`}>
                  {tab_.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map(i => (
              <div key={i} className="card h-48 animate-pulse bg-surface-2" />
            ))}
          </div>
        ) : (
          <>
            {/* ── TAB: DISCOVER ───────────────────────────── */}
            {tab === "discover" && (
              <div>
                {/* Search + Filters */}
                <div className="flex flex-wrap gap-2 mb-4">
                  {/* Search */}
                  <input
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    placeholder={t("courses.search_placeholder") || "Search courses…"}
                    className="border border-border rounded-lg px-3 py-1.5 text-sm font-serif bg-bg focus:outline-none focus:border-ink w-48"
                  />
                  {/* Specialty filter */}
                  <div className="flex flex-wrap gap-1.5">
                    {["all", ...specialties].map(sp => (
                      <button
                        key={sp}
                        onClick={() => setFilterSpecialty(sp)}
                        className={`px-3 py-1 rounded-full font-syne text-xs font-semibold border transition-colors ${
                          filterSpecialty === sp
                            ? "bg-ink text-white border-ink"
                            : "border-border text-ink-3 hover:border-ink-3 hover:text-ink"
                        }`}
                      >
                        {sp === "all" ? (t("courses.all_specialties") || "All specialties") : sp}
                      </button>
                    ))}
                  </div>
                  {/* Difficulty filter */}
                  <div className="flex gap-1.5 ml-auto">
                    {["all", "beginner", "intermediate", "advanced"].map(d => (
                      <button
                        key={d}
                        onClick={() => setFilterDifficulty(d)}
                        className={`px-3 py-1 rounded-full font-syne text-xs font-semibold border transition-colors ${
                          filterDifficulty === d
                            ? "bg-ink text-white border-ink"
                            : "border-border text-ink-3 hover:border-ink-3 hover:text-ink"
                        }`}
                      >
                        {d === "all" ? (t("courses.all_levels") || "All levels") : (t(DIFFICULTY_LABEL_KEY[d] as any) || d)}
                      </button>
                    ))}
                  </div>
                </div>

                {filteredPublic.length === 0 ? (
                  <div className="text-center py-12 text-ink-3 font-serif text-sm">No courses found</div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredPublic.map(course => (
                      <DiscoverCard
                        key={course.id}
                        course={course}
                        isEnrolled={enrolledIds.has(course.id)}
                        onEnroll={handleEnroll}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* ── TAB: MY COURSES ─────────────────────────── */}
            {tab === "enrolled" && (
              <div>
                {enrolled.length === 0 ? (
                  <div className="card p-10 text-center">
                    <div className="text-5xl mb-4">🎓</div>
                    <h2 className="font-syne font-bold text-lg text-ink mb-2">No courses yet</h2>
                    <p className="font-serif text-ink-3 text-sm max-w-sm mx-auto mb-5">
                      Explore our free platform courses or ask your teacher for an invite code.
                    </p>
                    <div className="flex gap-3 justify-center">
                      <button
                        onClick={() => setTab("discover")}
                        className="btn-primary px-5 py-2 text-sm"
                      >
                        Browse courses →
                      </button>
                      <button
                        onClick={() => setTab("join")}
                        className="btn-secondary px-5 py-2 text-sm"
                      >
                        Enter invite code
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {enrolled.map(course => (
                      <EnrolledCard key={course.id} course={course} onLeave={handleLeave} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* ── TAB: JOIN WITH CODE ─────────────────────── */}
            {tab === "join" && (
              <div className="max-w-md mx-auto">
                <div className="card p-6">
                  <div className="text-3xl mb-3">🔑</div>
                  <h2 className="font-syne font-bold text-lg text-ink mb-1">Join a teacher's course</h2>
                  <p className="font-serif text-ink-3 text-sm mb-5 leading-relaxed">
                    Enter the invite code your teacher shared with you. Codes are 8 characters (e.g. AB12CD34).
                  </p>
                  <form onSubmit={handleJoin} className="space-y-3">
                    <input
                      value={joinCode}
                      onChange={e => setJoinCode(e.target.value.toUpperCase())}
                      placeholder="Enter invite code (e.g. AB12CD34)"
                      maxLength={16}
                      className="w-full border border-border rounded-xl px-4 py-3 font-mono text-sm text-ink bg-surface focus:outline-none focus:border-ink text-center tracking-widest uppercase"
                    />
                    {joinMsg && (
                      <p className={`text-xs font-serif ${joinMsg.type === "success" ? "text-green" : "text-red"}`}>
                        {joinMsg.type === "success" ? "✓ " : "✗ "}{joinMsg.text}
                      </p>
                    )}
                    <button
                      type="submit"
                      disabled={joining || joinCode.trim().length < 6}
                      className="btn-primary w-full py-2.5 disabled:opacity-50"
                    >
                      {joining ? "Joining…" : "Join course →"}
                    </button>
                  </form>
                </div>

                {/* Info boxes */}
                <div className="mt-5 space-y-3">
                  <div className="card p-4 flex items-start gap-3">
                    <span className="text-xl flex-shrink-0">👨‍🏫</span>
                    <div>
                      <div className="font-syne font-bold text-sm text-ink mb-0.5">Are you a teacher?</div>
                      <p className="font-serif text-xs text-ink-3 leading-relaxed">
                        Create your own course, add modules, and share the invite code with your students.
                      </p>
                      <Link href="/teacher/courses/new" className="inline-block mt-2 text-xs font-syne font-semibold text-ink hover:text-accent underline">
                        Create a course →
                      </Link>
                    </div>
                  </div>
                  <div className="card p-4 flex items-start gap-3">
                    <span className="text-xl flex-shrink-0">📚</span>
                    <div>
                      <div className="font-syne font-bold text-sm text-ink mb-0.5">Free platform courses</div>
                      <p className="font-serif text-xs text-ink-3 leading-relaxed">
                        No invite code needed — browse and enroll in our curated courses.
                      </p>
                      <button
                        onClick={() => setTab("discover")}
                        className="inline-block mt-2 text-xs font-syne font-semibold text-ink hover:text-accent underline"
                      >
                        Browse courses →
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
