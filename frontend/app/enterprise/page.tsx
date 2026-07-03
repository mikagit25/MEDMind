"use client";

import { useState } from "react";
import Link from "next/link";
import { useI18n } from "@/lib/i18n";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { ArticleNav } from "@/components/layout/ArticleNav";

// ── Pricing config (change here, not in JSX) ─────────────────────────────────
const PRICING = [
  {
    key:   "starter" as const,
    color: "border-border",
    badge: null,
    features: [
      "Team dashboard & progress tracking",
      "All 125+ existing modules",
      "7 languages",
      "Mobile app (iOS & Android)",
      "Monthly progress reports",
      "Email support",
    ],
  },
  {
    key:   "business" as const,
    color: "border-red",
    badge: true,
    features: [
      "Everything in Starter",
      "Priority support (< 4h response)",
      "Onboarding call with our team",
      "Custom branding (your logo)",
      "Advanced analytics dashboard",
      "Dedicated account manager",
    ],
  },
  {
    key:   "enterprise" as const,
    color: "border-ink",
    badge: null,
    features: [
      "Everything in Business",
      "Custom module development",
      "SSO / SAML integration",
      "SLA guarantee",
      "Dedicated account manager",
      "Custom contract & invoicing",
    ],
  },
];

const FOR_WHOM = [
  { icon: "🐾", key: "vet"   as const },
  { icon: "🏥", key: "clinic" as const },
  { icon: "🎓", key: "uni"   as const },
  { icon: "🤝", key: "assoc" as const },
];

const FEATURES = [
  { icon: "📊", key: "dash"    as const },
  { icon: "📈", key: "report"  as const },
  { icon: "🌍", key: "lang"    as const },
  { icon: "📱", key: "offline" as const },
  { icon: "🤖", key: "ai"      as const },
  { icon: "🔧", key: "custom"  as const },
];

const PERSONAL_DOMAINS = [
  "gmail.com","yahoo.com","hotmail.com","outlook.com",
  "icloud.com","mail.ru","yandex.ru","yandex.com",
  "protonmail.com","proton.me","aol.com","live.com",
];

// ── Demo form ─────────────────────────────────────────────────────────────────

function DemoForm() {
  const { t } = useI18n();
  const e = (k: string) => (t as any).enterprise?.[k] ?? k;

  const [form, setForm] = useState({
    first_name: "", last_name: "", email: "",
    company: "", job_title: "", team_size: "", use_case: "", message: "",
  });
  const [errors,  setErrors]  = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [apiError, setApiError] = useState("");

  function validate() {
    const errs: Record<string, string> = {};
    if (!form.first_name.trim()) errs.first_name = "Required";
    if (!form.last_name.trim())  errs.last_name  = "Required";
    if (!form.company.trim())    errs.company    = "Required";
    if (!form.job_title.trim())  errs.job_title  = "Required";
    if (!form.team_size)         errs.team_size  = "Required";
    if (!form.use_case)          errs.use_case   = "Required";
    if (!form.email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
      errs.email = "Invalid email";
    } else {
      const domain = form.email.split("@")[1]?.toLowerCase();
      if (domain && PERSONAL_DOMAINS.includes(domain)) {
        errs.email = e("form_personal_email");
      }
    }
    return errs;
  }

  async function handleSubmit(ev: React.FormEvent) {
    ev.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});
    setLoading(true);
    setApiError("");
    try {
      const resp = await fetch("/api/v1/enterprise/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          first_name: form.first_name,
          last_name:  form.last_name,
          email:      form.email,
          company:    form.company,
          job_title:  form.job_title,
          team_size:  form.team_size,
          use_case:   form.use_case,
          message:    form.message || undefined,
        }),
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        const msg = data?.detail?.[0]?.msg ?? data?.detail ?? e("form_error");
        setApiError(msg);
      } else {
        setSuccess(true);
      }
    } catch {
      setApiError(e("form_error"));
    } finally {
      setLoading(false);
    }
  }

  function field(name: keyof typeof form, label: string, type = "text") {
    return (
      <div>
        <label className="block text-sm font-syne font-semibold text-ink mb-1">{label}</label>
        <input
          type={type}
          value={form[name]}
          onChange={e => setForm(p => ({ ...p, [name]: e.target.value }))}
          className={`w-full border rounded-lg px-3 py-2.5 text-sm bg-bg text-ink focus:outline-none focus:ring-2 focus:ring-red/40 transition ${errors[name] ? "border-red" : "border-border"}`}
        />
        {errors[name] && <p className="text-red text-xs mt-1">{errors[name]}</p>}
      </div>
    );
  }

  if (success) {
    return (
      <div className="bg-green-2/10 border border-green-2/30 rounded-2xl p-10 text-center">
        <div className="text-4xl mb-4">✅</div>
        <p className="font-syne font-bold text-xl text-ink">{e("form_success")}</p>
      </div>
    );
  }

  const sizeOptions = [
    { val: "1-10",   label: e("size_1")   },
    { val: "11-25",  label: e("size_11")  },
    { val: "26-100", label: e("size_26")  },
    { val: "100+",   label: e("size_100") },
  ];
  const caseOptions = [
    { val: "Veterinary company", label: e("case_vet")    },
    { val: "Clinic or hospital", label: e("case_clinic") },
    { val: "University",         label: e("case_uni")    },
    { val: "Association",        label: e("case_assoc")  },
    { val: "Other",              label: e("case_other")  },
  ];

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid sm:grid-cols-2 gap-4">
        {field("first_name", e("form_first"))}
        {field("last_name",  e("form_last"))}
      </div>
      {field("email",    e("form_email"),   "email")}
      {field("company",  e("form_company"))}
      {field("job_title", e("form_title_field"))}

      <div className="grid sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-syne font-semibold text-ink mb-1">{e("form_size")}</label>
          <select
            value={form.team_size}
            onChange={ev => setForm(p => ({ ...p, team_size: ev.target.value }))}
            className={`w-full border rounded-lg px-3 py-2.5 text-sm bg-bg text-ink focus:outline-none focus:ring-2 focus:ring-red/40 ${errors.team_size ? "border-red" : "border-border"}`}
          >
            <option value="">—</option>
            {sizeOptions.map(o => <option key={o.val} value={o.val}>{o.label}</option>)}
          </select>
          {errors.team_size && <p className="text-red text-xs mt-1">{errors.team_size}</p>}
        </div>
        <div>
          <label className="block text-sm font-syne font-semibold text-ink mb-1">{e("form_usecase")}</label>
          <select
            value={form.use_case}
            onChange={ev => setForm(p => ({ ...p, use_case: ev.target.value }))}
            className={`w-full border rounded-lg px-3 py-2.5 text-sm bg-bg text-ink focus:outline-none focus:ring-2 focus:ring-red/40 ${errors.use_case ? "border-red" : "border-border"}`}
          >
            <option value="">—</option>
            {caseOptions.map(o => <option key={o.val} value={o.val}>{o.label}</option>)}
          </select>
          {errors.use_case && <p className="text-red text-xs mt-1">{errors.use_case}</p>}
        </div>
      </div>

      <div>
        <label className="block text-sm font-syne font-semibold text-ink mb-1">{e("form_message")}</label>
        <textarea
          rows={3}
          value={form.message}
          onChange={ev => setForm(p => ({ ...p, message: ev.target.value }))}
          className="w-full border border-border rounded-lg px-3 py-2.5 text-sm bg-bg text-ink focus:outline-none focus:ring-2 focus:ring-red/40 resize-none"
        />
      </div>

      {apiError && (
        <p className="text-red text-sm bg-red/5 border border-red/20 rounded-lg px-4 py-2">{apiError}</p>
      )}

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-red hover:bg-red/90 text-white font-syne font-bold py-3 rounded-xl text-base transition-colors disabled:opacity-60"
      >
        {loading ? "Sending…" : e("form_submit")}
      </button>
    </form>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function EnterprisePage() {
  const { t, locale } = useI18n();
  const e = (k: string) => (t as any).enterprise?.[k] ?? k;

  return (
    <>
      {/* Schema.org */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify({
          "@context": "https://schema.org",
          "@type": "WebPage",
          name: e("meta_title"),
          description: e("meta_desc"),
          url: "https://medmind.pro/enterprise",
        }) }}
      />

      <div className="min-h-screen bg-bg">
        <ArticleNav />

        {/* ── Hero ─────────────────────────────────────────────────────── */}
        <section className="bg-gradient-to-b from-slate-50 to-bg pt-20 pb-16 px-6">
          <div className="max-w-4xl mx-auto text-center">
            <div className="inline-flex items-center gap-2 bg-red/10 border border-red/20 px-3 py-1 rounded-full font-syne font-semibold text-xs text-red mb-6">
              <span className="w-1.5 h-1.5 rounded-full bg-red" />
              MedMind for Teams
            </div>
            <h1 className="font-syne font-extrabold text-4xl sm:text-5xl text-ink leading-tight mb-6">
              {e("hero_title")}
            </h1>
            <p className="text-ink-2 text-lg max-w-2xl mx-auto mb-8 leading-relaxed">
              {e("hero_subtitle")}
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center mb-5">
              <a
                href="#demo-form"
                className="inline-flex items-center justify-center gap-2 bg-red hover:bg-red/90 text-white font-syne font-bold px-8 py-4 rounded-xl text-base transition-colors"
              >
                {e("cta_demo")} →
              </a>
              <a
                href="#pricing"
                className="inline-flex items-center justify-center border border-border hover:border-ink text-ink-2 hover:text-ink font-syne font-semibold px-8 py-4 rounded-xl text-base transition-colors"
              >
                {e("cta_pricing")}
              </a>
            </div>
            <p className="text-ink-3 text-sm font-syne">{e("trust_line")}</p>
          </div>
        </section>

        {/* ── For whom ─────────────────────────────────────────────────── */}
        <section className="bg-surface border-y border-border py-14 px-6">
          <div className="max-w-5xl mx-auto">
            <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink text-center mb-10">
              {e("for_whom_title")}
            </h2>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {FOR_WHOM.map(({ icon, key }) => (
                <div key={key} className="bg-bg border border-border rounded-xl p-5">
                  <div className="text-3xl mb-3">{icon}</div>
                  <h3 className="font-syne font-bold text-sm text-ink mb-2">
                    {e(`for_whom_${key}`)}
                  </h3>
                  <p className="text-ink-3 text-xs font-serif leading-relaxed">
                    {e(`for_whom_${key}_d`)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Features ─────────────────────────────────────────────────── */}
        <section className="py-14 px-6">
          <div className="max-w-5xl mx-auto">
            <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink text-center mb-10">
              {e("features_title")}
            </h2>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {FEATURES.map(({ icon, key }) => (
                <div key={key} className="flex gap-4 p-5 bg-surface border border-border rounded-xl">
                  <span className="text-2xl flex-shrink-0">{icon}</span>
                  <div>
                    <h3 className="font-syne font-bold text-sm text-ink mb-1">
                      {e(`feat_${key}`)}
                    </h3>
                    <p className="text-ink-3 text-xs font-serif leading-relaxed">
                      {e(`feat_${key}_d`)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Pricing ──────────────────────────────────────────────────── */}
        <section id="pricing" className="bg-surface border-y border-border py-16 px-6">
          <div className="max-w-5xl mx-auto">
            <div className="text-center mb-10">
              <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink mb-2">
                {e("pricing_title")}
              </h2>
              <p className="text-ink-3 text-sm">{e("pricing_sub")}</p>
            </div>
            <div className="grid sm:grid-cols-3 gap-6">
              {PRICING.map(plan => (
                <div
                  key={plan.key}
                  className={`relative rounded-2xl border-2 ${plan.color} p-6 bg-bg flex flex-col`}
                >
                  {plan.badge && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                      <span className="bg-red text-white font-syne font-bold text-xs px-3 py-1 rounded-full whitespace-nowrap">
                        {e("tier_business_badge")}
                      </span>
                    </div>
                  )}
                  <div className="mb-4">
                    <h3 className="font-syne font-extrabold text-xl text-ink">
                      {e(`tier_${plan.key}`)}
                    </h3>
                    <p className="text-ink-3 text-xs font-syne mt-0.5">
                      {e(`tier_${plan.key}_users`)}
                    </p>
                  </div>
                  <div className="mb-1">
                    <span className="font-syne font-extrabold text-2xl text-ink">
                      {e(`tier_${plan.key}_price`)}
                    </span>
                  </div>
                  <p className="text-ink-3 text-xs font-syne mb-5">
                    {e(`tier_${plan.key}_note`)}
                  </p>
                  <ul className="space-y-2 mb-6 flex-1">
                    {plan.features.map(f => (
                      <li key={f} className="flex gap-2 items-start text-xs font-serif text-ink-2">
                        <span className="text-green-2 flex-shrink-0 mt-0.5">✓</span>
                        {f}
                      </li>
                    ))}
                  </ul>
                  <a
                    href="#demo-form"
                    className={`block text-center font-syne font-bold text-sm py-2.5 rounded-xl transition-colors ${
                      plan.badge
                        ? "bg-red text-white hover:bg-red/90"
                        : plan.key === "enterprise"
                        ? "bg-ink text-white hover:bg-ink/80"
                        : "border border-border text-ink hover:bg-surface"
                    }`}
                  >
                    {e(plan.key === "starter" ? "cta_trial" : plan.key === "business" ? "cta_request" : "cta_contact")}
                  </a>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Onboarding steps ─────────────────────────────────────────── */}
        <section className="py-14 px-6">
          <div className="max-w-4xl mx-auto">
            <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink text-center mb-10">
              {e("onboard_title")}
            </h2>
            <div className="grid sm:grid-cols-3 gap-6">
              {([1, 2, 3] as const).map(step => (
                <div key={step} className="text-center">
                  <div className="w-10 h-10 rounded-full bg-red text-white font-syne font-extrabold text-lg flex items-center justify-center mx-auto mb-4">
                    {step}
                  </div>
                  <h3 className="font-syne font-bold text-sm text-ink mb-2">
                    {e(`step${step}_title`)}
                  </h3>
                  <p className="text-ink-3 text-xs font-serif leading-relaxed">
                    {e(`step${step}_body`)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Demo form ─────────────────────────────────────────────────── */}
        <section id="demo-form" className="bg-surface border-y border-border py-16 px-6">
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-8">
              <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink mb-2">
                {e("form_title")}
              </h2>
              <p className="text-ink-3 text-sm">{e("form_subtitle")}</p>
            </div>
            <DemoForm />
          </div>
        </section>

        <PublicFooter locale={locale} />
      </div>
    </>
  );
}
