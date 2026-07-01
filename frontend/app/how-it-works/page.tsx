"use client";
import { useState } from "react";
import { useT, useI18n } from "@/lib/i18n";
import Link from "next/link";

const LANGS = [
  { value: "en", flag: "🇬🇧" }, { value: "ru", flag: "🇷🇺" },
  { value: "de", flag: "🇩🇪" }, { value: "fr", flag: "🇫🇷" },
  { value: "ar", flag: "🇸🇦" }, { value: "tr", flag: "🇹🇷" },
  { value: "es", flag: "🇪🇸" },
] as const;

// ── Browser frame wrapper ─────────────────────────────────────
function Browser({ url, children, className = "" }: { url: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl overflow-hidden border border-border shadow-2xl ${className}`}>
      <div className="bg-surface-2 px-3 py-2 flex items-center gap-2 border-b border-border">
        <div className="flex gap-1.5 shrink-0">
          <div className="w-2.5 h-2.5 rounded-full bg-red-light border border-red/20" />
          <div className="w-2.5 h-2.5 rounded-full bg-amber-light border border-amber/20" />
          <div className="w-2.5 h-2.5 rounded-full bg-green-light border border-green/20" />
        </div>
        <div className="flex-1 bg-bg rounded text-[10px] text-ink-3 font-mono px-2 py-0.5 truncate border border-border">
          medmind.pro{url}
        </div>
      </div>
      <div className="bg-bg">{children}</div>
    </div>
  );
}

// ── UI Mockups ────────────────────────────────────────────────

function MockAITutor() {
  return (
    <div className="p-3 text-xs font-sans">
      <div className="flex items-center gap-2 mb-3 pb-2 border-b border-border">
        <div className="w-6 h-6 rounded-full bg-ink flex items-center justify-center text-[10px] text-white font-bold">AI</div>
        <span className="font-syne font-bold text-ink text-[11px]">AI Tutor · Cardiology</span>
        <span className="ml-auto text-[9px] bg-green-light text-green px-1.5 py-0.5 rounded-full font-syne">PubMed live</span>
      </div>
      <div className="space-y-2">
        <div className="bg-surface-2 rounded-lg p-2.5 max-w-[85%]">
          <p className="text-ink-2 text-[10px] leading-relaxed">What is first-line treatment for acute HFrEF?</p>
        </div>
        <div className="bg-amber-light rounded-lg p-2.5 ml-auto max-w-[90%]">
          <p className="text-ink text-[10px] leading-relaxed mb-1.5">
            First-line: <strong>IV furosemide</strong> for decongestion + O₂ to SpO₂ &gt;94%. Add vasodilators if SBP &gt;90 mmHg.
          </p>
          <div className="flex gap-1 flex-wrap">
            <span className="text-[8px] bg-blue-light text-blue px-1.5 py-0.5 rounded font-mono">PMID: 37642891</span>
            <span className="text-[8px] bg-blue-light text-blue px-1.5 py-0.5 rounded font-mono">ESC 2023</span>
          </div>
        </div>
        <div className="bg-surface-2 rounded-lg p-2.5 max-w-[75%]">
          <p className="text-ink-2 text-[10px]">Explain SGLT2 inhibitor role in HF</p>
        </div>
        <div className="flex items-center gap-1 mt-2">
          <div className="flex-1 bg-surface rounded border border-border px-2 py-1 text-[9px] text-ink-3">Ask a follow-up…</div>
          <div className="bg-ink rounded px-2 py-1 text-[9px] text-white font-syne">Send</div>
        </div>
      </div>
    </div>
  );
}

function MockModules() {
  const modules = [
    { name: "Heart Failure", specialty: "Cardiology", progress: 72, icon: "❤️" },
    { name: "Stroke Management", specialty: "Neurology", progress: 45, icon: "🧠" },
    { name: "Sepsis Protocol", specialty: "IM", progress: 91, icon: "🩸" },
    { name: "Pediatric Fever", specialty: "Pediatrics", progress: 20, icon: "👶" },
  ];
  return (
    <div className="p-3 text-xs">
      <div className="flex items-center justify-between mb-2.5">
        <span className="font-syne font-bold text-ink text-[11px]">Module Library</span>
        <span className="text-[9px] text-ink-3 bg-surface-2 px-2 py-0.5 rounded-full font-syne">125+ modules</span>
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        {modules.map(m => (
          <div key={m.name} className="bg-surface rounded-lg p-2 border border-border">
            <div className="flex items-center gap-1 mb-1.5">
              <span className="text-sm">{m.icon}</span>
              <div>
                <p className="text-[9px] font-syne font-bold text-ink leading-tight">{m.name}</p>
                <p className="text-[8px] text-ink-3">{m.specialty}</p>
              </div>
            </div>
            <div className="h-1 bg-bg-2 rounded-full overflow-hidden">
              <div className="h-full bg-amber rounded-full" style={{ width: `${m.progress}%` }} />
            </div>
            <p className="text-[8px] text-ink-3 mt-0.5">{m.progress}% complete</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function MockFlashcard() {
  return (
    <div className="p-4 text-xs">
      <div className="flex items-center justify-between mb-3">
        <span className="font-syne font-bold text-ink text-[11px]">Flashcards · SM-2</span>
        <span className="text-[9px] text-amber bg-amber-light px-2 py-0.5 rounded-full font-syne">Card 14 / 32</span>
      </div>
      <div className="bg-surface rounded-xl border-2 border-amber/20 p-4 text-center mb-3 shadow-sm">
        <div className="text-[10px] text-ink-3 font-syne mb-2 uppercase tracking-wider">Question</div>
        <p className="text-ink text-[11px] font-syne font-bold leading-relaxed">
          What ECG finding is pathognomonic for Wolff-Parkinson-White syndrome?
        </p>
      </div>
      <div className="bg-amber-light rounded-xl border border-amber/30 p-3 text-center mb-3">
        <div className="text-[10px] text-ink-3 font-syne mb-1 uppercase tracking-wider">Answer</div>
        <p className="text-[10px] text-ink leading-relaxed">
          Short PR (&lt;120 ms) + <strong>delta wave</strong> (slurred QRS upstroke) due to ventricular pre-excitation via accessory pathway
        </p>
      </div>
      <div className="flex gap-1.5 justify-center">
        {(["❌ Again", "😕 Hard", "✓ Good", "⚡ Easy"] as const).map((l, i) => (
          <div key={l} className={`flex-1 text-center py-1.5 rounded-lg text-[9px] font-syne font-bold ${
            i === 0 ? "bg-red-light text-red" : i === 1 ? "bg-surface-2 text-ink-2" : i === 2 ? "bg-green-light text-green" : "bg-blue-light text-blue"
          }`}>
            {l}
          </div>
        ))}
      </div>
    </div>
  );
}

function MockClinicalCase() {
  return (
    <div className="p-3 text-xs">
      <div className="flex items-center gap-2 mb-2.5">
        <span className="text-[9px] bg-red-light text-red px-1.5 py-0.5 rounded-full font-syne font-bold">CASE · ED</span>
        <span className="font-syne font-bold text-ink text-[11px]">42F · Chest Pain</span>
      </div>
      <div className="bg-surface-2 rounded-lg p-2.5 mb-2 border border-border">
        <p className="text-ink-2 text-[10px] leading-relaxed mb-1.5">
          42-year-old woman with 2 hours of crushing substernal chest pain radiating to the left arm. HR 102, BP 145/90, SpO₂ 96%.
        </p>
        <div className="grid grid-cols-3 gap-1">
          {([["❤️", "HR 102", "text-amber"], ["🫁", "SpO₂ 96%", "text-blue"], ["📊", "BP 145/90", "text-red"]] as [string,string,string][]).map(([e, v, c]) => (
            <div key={v} className="bg-bg rounded p-1.5 text-center">
              <div className="text-sm">{e}</div>
              <div className={`text-[9px] font-mono font-bold ${c}`}>{v}</div>
            </div>
          ))}
        </div>
      </div>
      <div className="text-[10px] text-ink-2 font-syne font-bold mb-1.5">Your next step?</div>
      <div className="space-y-1">
        {["A. 12-lead ECG + troponin ✓", "B. Chest X-ray", "C. Echocardiogram"].map((opt, i) => (
          <div key={opt} className={`rounded-lg px-2 py-1.5 text-[9px] font-syne ${
            i === 0 ? "bg-green-light text-green border border-green/20 font-bold" : "bg-surface border border-border text-ink-2"
          }`}>
            {opt}
          </div>
        ))}
      </div>
    </div>
  );
}

function MockDrugDB() {
  return (
    <div className="p-3 text-xs">
      <div className="flex items-center gap-1.5 mb-2.5">
        <div className="flex-1 bg-surface border border-border rounded px-2 py-1.5 text-[10px] text-ink">Metformin</div>
        <div className="bg-ink text-white rounded px-2 py-1.5 text-[10px] font-syne">Search</div>
      </div>
      <div className="bg-surface rounded-lg border border-border p-2.5">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-lg">💊</span>
          <div>
            <p className="font-syne font-bold text-ink text-[11px]">Metformin HCl</p>
            <p className="text-[9px] text-ink-3">Biguanide · Type 2 DM</p>
          </div>
          <span className="ml-auto text-[8px] bg-green-light text-green px-1.5 py-0.5 rounded-full">First-line</span>
        </div>
        <div className="grid grid-cols-2 gap-1.5 text-[9px]">
          <div className="bg-bg-2 rounded p-1.5">
            <p className="text-ink-3 mb-0.5">Dose</p>
            <p className="text-ink font-bold">500–2000 mg/day</p>
          </div>
          <div className="bg-bg-2 rounded p-1.5">
            <p className="text-ink-3 mb-0.5">Onset</p>
            <p className="text-ink font-bold">1–2 weeks</p>
          </div>
        </div>
        <div className="mt-1.5 text-[9px] bg-red-light rounded p-1.5">
          <span className="text-red font-bold">⚠️ CI:</span>
          <span className="text-ink-2 ml-1">eGFR &lt;30, iodinated contrast</span>
        </div>
      </div>
    </div>
  );
}

function MockHealthHub() {
  return (
    <div className="p-3 text-xs">
      <div className="flex items-center justify-between mb-2.5">
        <span className="font-syne font-bold text-ink text-[11px]">Health Hub</span>
        <span className="text-[9px] text-blue bg-blue-light px-1.5 py-0.5 rounded-full font-syne">📱 Telegram synced</span>
      </div>
      <div className="bg-surface rounded-lg border border-border p-2 mb-2">
        <div className="flex items-center gap-2 mb-1.5">
          <div className="w-6 h-6 rounded-full bg-amber-light flex items-center justify-center text-sm">👨</div>
          <div>
            <p className="text-[10px] font-syne font-bold text-ink">45 yr · Male</p>
            <p className="text-[8px] text-ink-3">💊 Lisinopril · Atorvastatin</p>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-1 text-center">
          {[["🩸", "Glucose", "5.4 mmol"], ["❤️", "BP", "128/82"], ["⚖️", "Weight", "82 kg"]].map(([e, l, v]) => (
            <div key={l} className="bg-bg-2 rounded p-1">
              <div className="text-sm">{e}</div>
              <div className="text-[8px] text-ink-3">{l}</div>
              <div className="text-[9px] font-bold text-ink">{v}</div>
            </div>
          ))}
        </div>
      </div>
      <div className="space-y-1">
        <div className="bg-amber-light border border-amber/20 rounded-lg p-1.5">
          <div className="text-[9px] font-syne font-bold text-amber mb-0.5">🩸 Type 2 Diabetes</div>
          <div className="text-[8px] text-ink-3">HbA1c target: &lt;7% · Next check: 3 mo</div>
        </div>
        <div className="bg-surface-2 border border-border rounded-lg p-1.5">
          <div className="text-[9px] font-syne font-bold text-ink mb-0.5">❤️ Hypertension</div>
          <div className="text-[8px] text-ink-3">BP on target · Medication adherent</div>
        </div>
      </div>
    </div>
  );
}

function MockTelegram() {
  return (
    <div className="p-3 text-xs bg-[#e5ddd5]">
      <div className="flex items-center gap-2 mb-3 bg-[#075e54] -mx-3 -mt-3 px-3 py-2.5">
        <div className="w-7 h-7 rounded-full bg-white flex items-center justify-center text-sm">🏥</div>
        <div>
          <p className="text-white font-bold text-[11px] font-syne">MedMind AI Bot</p>
          <p className="text-white/70 text-[8px]">online</p>
        </div>
      </div>
      <div className="space-y-1.5 mt-2">
        <div className="bg-white rounded-xl rounded-tl-none p-2 max-w-[85%] shadow-sm">
          <p className="text-[10px] text-gray-800">Головная боль 3 дня, температура 37.8</p>
        </div>
        <div className="bg-[#dcf8c6] rounded-xl rounded-tr-none p-2 max-w-[85%] ml-auto shadow-sm">
          <p className="text-[10px] text-gray-800 leading-relaxed mb-1">
            ⚠️ Сочетание головной боли + температуры — нужно исключить менингит.
          </p>
          <p className="text-[9px] text-gray-500">Есть скованность шеи? Светобоязнь?</p>
        </div>
        <div className="bg-white rounded-xl rounded-tl-none p-2 max-w-[60%] shadow-sm">
          <p className="text-[10px] text-gray-800">Нет, просто ОРВИ наверное</p>
        </div>
        <div className="flex gap-1 flex-wrap">
          {["🤒 Симптомы", "💊 Препараты", "📍 Тест"].map(b => (
            <div key={b} className="bg-white border border-gray-200 rounded-full px-2 py-0.5 text-[8px] text-[#075e54] font-bold">{b}</div>
          ))}
        </div>
      </div>
    </div>
  );
}

function MockImaging() {
  return (
    <div className="p-3 text-xs">
      <div className="flex items-center justify-between mb-2">
        <span className="font-syne font-bold text-ink text-[11px]">Imaging Library</span>
        <span className="text-[9px] text-ink-3 bg-surface-2 px-1.5 py-0.5 rounded font-syne">2,400+ images</span>
      </div>
      <div className="aspect-video bg-[#1a1814] rounded-lg mb-2 flex items-center justify-center relative overflow-hidden">
        <div className="text-white/20 text-5xl">🫁</div>
        <div className="absolute top-1.5 right-1.5 text-[8px] text-white/50 font-mono bg-black/40 px-1.5 py-0.5 rounded">PA Chest · X-Ray</div>
        <div className="absolute bottom-1.5 left-1.5 text-[8px] text-white/50 font-mono bg-black/40 px-1.5 py-0.5 rounded">Normal CXR</div>
        <div className="absolute bottom-1.5 right-1.5 bg-amber text-white text-[8px] px-1.5 py-0.5 rounded font-syne">🤖 AI Analysis</div>
      </div>
      <div className="bg-amber-light border border-amber/20 rounded-lg p-2">
        <p className="text-[9px] text-ink font-syne font-bold mb-0.5">AI Findings:</p>
        <p className="text-[9px] text-ink-2 leading-relaxed">Normal cardiac silhouette. Clear lung fields. No pleural effusion or consolidation.</p>
      </div>
    </div>
  );
}

function MockProgress() {
  return (
    <div className="p-3 text-xs">
      <div className="flex items-center justify-between mb-3">
        <div>
          <p className="font-syne font-bold text-ink text-[11px]">Your Progress</p>
          <p className="text-[9px] text-ink-3">Level 4 · Specialist</p>
        </div>
        <div className="text-right">
          <p className="font-syne font-black text-lg text-amber leading-none">🔥 14</p>
          <p className="text-[8px] text-ink-3">day streak</p>
        </div>
      </div>
      <div className="mb-2.5">
        <div className="flex justify-between text-[9px] text-ink-3 mb-1">
          <span>3,240 XP</span><span>Next: 5,000 XP</span>
        </div>
        <div className="h-2 bg-bg-2 rounded-full overflow-hidden">
          <div className="h-full rounded-full bg-gradient-to-r from-red to-amber" style={{ width: "65%" }} />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-1 text-center mb-2">
        {[["82%", "Cardiology"], ["54%", "Neurology"], ["91%", "Surgery"]].map(([v, l]) => (
          <div key={l} className="bg-surface-2 rounded p-1.5">
            <p className="font-syne font-black text-ink text-[11px]">{v}</p>
            <p className="text-[8px] text-ink-3">{l}</p>
          </div>
        ))}
      </div>
      <div className="flex gap-0.5">
        {Array.from({ length: 14 }, (_, i) => (
          <div key={i} className={`flex-1 h-3 rounded-sm ${i < 11 ? "bg-green" : i < 13 ? "bg-green-light border border-green/30" : "bg-bg-2"}`} />
        ))}
      </div>
      <p className="text-[8px] text-ink-3 mt-0.5 text-right">Last 14 days</p>
    </div>
  );
}

function MockCalculator() {
  return (
    <div className="p-3 text-xs">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-base">🧮</span>
        <div>
          <p className="font-syne font-bold text-ink text-[11px]">CHA₂DS₂-VASc Score</p>
          <p className="text-[9px] text-ink-3">Stroke risk in non-valvular AF</p>
        </div>
      </div>
      <div className="space-y-1.5 mb-3">
        {([["Age ≥75", "2 pts", true], ["Hypertension", "1 pt", true], ["Diabetes", "1 pt", false], ["Prior stroke/TIA", "2 pts", false]] as [string, string, boolean][]).map(([l, p, c]) => (
          <div key={l} className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <div className={`w-3.5 h-3.5 rounded border flex items-center justify-center text-[8px] ${c ? "bg-ink border-ink text-white" : "border-border-2"}`}>
                {c ? "✓" : ""}
              </div>
              <span className="text-[9px] text-ink-2">{l}</span>
            </div>
            <span className={`text-[9px] font-mono font-bold ${c ? "text-red" : "text-ink-3"}`}>{p}</span>
          </div>
        ))}
      </div>
      <div className="bg-red-light border border-red/20 rounded-lg p-2 text-center">
        <p className="text-red font-syne font-black text-xl">3</p>
        <p className="text-[9px] text-red font-bold">High Risk · Anticoagulation recommended</p>
        <p className="text-[8px] text-ink-3 mt-0.5">Annual stroke risk: ~3.2%</p>
      </div>
    </div>
  );
}

// ── Feature sections (built inside component to allow i18n) ──
type FeatureItem = { title: string; desc: string; badge: string; extras: string[]; mockup: React.ReactNode; flip: boolean };
type FeatureSection = { id: string; tab: string; items: FeatureItem[] };

const FEATURES_RAW: Array<Omit<FeatureSection, "tab"> & { tabKey: string }> = [
  {
    id: "ai",
    tabKey: "feat_tab_ai",
    items: [
      {
        title: "AI Tutor with Live PubMed",
        desc: "Ask any medical question and get structured, cited answers grounded in real evidence. The AI searches PubMed in real-time before every response — no hallucinations, no outdated guidelines. Choose from Tutor, Socratic, Case, or Exam mode.",
        badge: "Powered by Claude",
        extras: ["4 learning modes: Tutor · Socratic · Case · Exam", "Live PubMed integration — every answer includes PMIDs", "Multilingual: 7 languages with auto-detection", "Unlimited for Pro users · 5/day on Free"],
        mockup: <MockAITutor />,
        flip: false,
      },
      {
        title: "Interactive Clinical Cases",
        desc: "Work through realistic patient encounters complete with vitals, labs, and imaging. The AI plays attending physician — guiding your differential, investigations, and management decisions in real time.",
        badge: "USMLE / MRCP / PLAB format",
        extras: ["ECG, X-ray, and lab interpretation built in", "Branching scenarios that change based on your choices", "Immediate feedback with evidence-based explanations", "Covers all major exam formats worldwide"],
        mockup: <MockClinicalCase />,
        flip: true,
      },
    ],
  },
  {
    id: "learning",
    tabKey: "feat_tab_learning",
    items: [
      {
        title: "82+ Structured Modules",
        desc: "Complete curriculum across 6 core specialties — Cardiology, Neurology, Surgery, Internal Medicine, Pediatrics, and OB/GYN. Each module is built around real clinical curricula with AI-generated lessons verified against current guidelines.",
        badge: "82+ modules · Growing",
        extras: ["6 core specialties + subspecialties", "AI-generated lessons with source citations", "Module-level progress tracking", "New modules added monthly based on user demand"],
        mockup: <MockModules />,
        flip: false,
      },
      {
        title: "Spaced Repetition Flashcards",
        desc: "500+ clinical flashcards using the SM-2 algorithm — the same science behind Anki. Cards appear exactly when you're about to forget, not a moment sooner. Rate difficulty and the algorithm auto-adjusts the next review interval.",
        badge: "SM-2 Algorithm",
        extras: ["Auto-generated from lesson content", "Community-verified for accuracy", "Due-card reminder notifications", "Per-deck retention stats and mastery scores"],
        mockup: <MockFlashcard />,
        flip: true,
      },
    ],
  },
  {
    id: "clinical",
    tabKey: "feat_tab_clinical",
    items: [
      {
        title: "Drug Database + Interaction Checker",
        desc: "Comprehensive drug reference for 5,000+ medications covering dosing, mechanisms, contraindications, monitoring parameters, and drug interactions. The interaction checker flags dangerous combinations instantly with severity grades.",
        badge: "5,000+ drugs",
        extras: ["Pediatric weight-based dosing included", "CYP450 interactions with clinical significance", "Renal and hepatic dose adjustment tables", "Pregnancy & lactation safety categories"],
        mockup: <MockDrugDB />,
        flip: false,
      },
      {
        title: "40+ Clinical Calculators",
        desc: "Evidence-based risk scores and clinical decision tools, each with full interpretation and management guidance. Results saved to your history — review past calculations and track how scores change over time.",
        badge: "40+ validated scores",
        extras: ["CHA₂DS₂-VASc · Wells · CURB-65 · SOFA · BMI · eGFR", "Each calculator linked to treatment guidelines", "Result history saved per patient or session", "Evidence level and guideline source shown"],
        mockup: <MockCalculator />,
        flip: true,
      },
    ],
  },
  {
    id: "imaging",
    tabKey: "feat_tab_imaging",
    items: [
      {
        title: "Medical Imaging Library + AI Analysis",
        desc: "2,400+ annotated radiology images spanning X-ray, CT, MRI, ultrasound, ECG, and histology. Study real pathology images with attending-level annotations, then upload your own for AI interpretation — including skin lesions, blood tests, and ECG photos from Telegram.",
        badge: "2,400+ images",
        extras: ["All modalities: XR · CT · MRI · Echo · ECG · Histo", "Upload your own images for AI analysis", "Annotated key findings with arrows and labels", "Differential diagnosis generated per image"],
        mockup: <MockImaging />,
        flip: false,
      },
      {
        title: "Health Hub — Personal Health Dashboard",
        desc: "A unified health profile that syncs between the web dashboard and Telegram bot. Patients and healthcare workers can track chronic conditions, log vitals, set medication reminders, monitor symptom patterns, and get disease-specific article recommendations.",
        badge: "Unique · No other platform has this",
        extras: ["10 chronic disease protocols: diabetes, HTN, asthma, CKD…", "Vitals tracking: glucose, BP, weight, SpO₂, temp", "Medication reminder scheduler with daily push", "Symptom history and mood timeline synced from Telegram"],
        mockup: <MockHealthHub />,
        flip: true,
      },
    ],
  },
  {
    id: "progress",
    tabKey: "feat_tab_progress",
    items: [
      {
        title: "Progress Dashboard & Gamification",
        desc: "XP points, level system, daily streaks, and a global leaderboard turn long-term study into a daily habit. See module completion rates, flashcard retention scores, and AI question history all in one place.",
        badge: "XP · Streaks · Leaderboard",
        extras: ["Daily streak calendar with heatmap view", "Specialty completion percentages", "25+ achievement badges to unlock", "Weekly digest report (Monday email)"],
        mockup: <MockProgress />,
        flip: false,
      },
      {
        title: "Telegram Bot — AI in Your Pocket",
        desc: "Full MedMind functionality without opening the browser. Ask medical questions, get triage advice, send ECG or blood test photos for AI interpretation, track your vitals, and set medication reminders — all in Telegram, in any language.",
        badge: "Works 24/7 · No app install",
        extras: ["Works in 7 languages — auto-detected from your message", "Photo analysis: ECG · blood tests · skin · X-rays", "Patient mode: plain-language explanations for non-clinicians", "Fully synced to your web account — history shared"],
        mockup: <MockTelegram />,
        flip: true,
      },
    ],
  },
];

const MINI_FEATURES = [
  { icon: "🌍", title: "7 Languages", desc: "EN · RU · DE · FR · ES · TR · AR — interfaces, AI, and articles" },
  { icon: "🦮", title: "Veterinary Module", desc: "Drug dosing database for dogs, cats, horses, birds, and exotic animals" },
  { icon: "🎓", title: "Educator Tools", desc: "Build courses, assign modules to students, track progress, export reports" },
  { icon: "📅", title: "Adaptive Study Plans", desc: "AI-generated weekly schedule based on your goal, specialty, and free time" },
  { icon: "📰", title: "Medical News", desc: "Daily clinical news curated, translated, and summarised — stay current" },
  { icon: "📖", title: "Article Library", desc: "1,000+ evidence-based articles on conditions, drugs, and procedures" },
  { icon: "🏆", title: "Achievements & Badges", desc: "25+ milestones: streaks, exam scores, first case, flashcard mastery" },
  { icon: "📤", title: "FHIR Export", desc: "Export your learning and health data in standard FHIR R4 format" },
  { icon: "🔍", title: "Global Search", desc: "Search across all modules, drugs, articles, and clinical cases instantly" },
  { icon: "📌", title: "Bookmarks & Notes", desc: "Save any lesson, drug, article, or case — add personal annotations" },
  { icon: "🌙", title: "Dark Mode", desc: "Full dark mode designed for night shifts and late study sessions" },
  { icon: "📱", title: "Fully Responsive", desc: "Desktop, tablet, mobile — no app install required, works in any browser" },
];

export default function HowItWorksPage() {
  const t = useT();
  const { locale, setLocale } = useI18n();
  const [menuOpen, setMenuOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("ai");
  const [openFAQ, setOpenFAQ] = useState<number | null>(null);

  const faq = t("how_it_works_page.faq") as unknown as { q: string; a: string }[];
  const cmpRows = t("how_it_works_page.cmp_rows") as unknown as string[][];
  const roles = t("how_it_works_page.roles") as unknown as { role: string; icon: string; description: string; features: string[] }[];

  const localeFeatures = t("how_it_works_page.features") as unknown as Array<{ id: string; items: Array<{ title: string; desc: string; badge: string; extras: string[] }> }> | undefined;
  const FEATURES: FeatureSection[] = FEATURES_RAW.map((f, fi) => {
    const locF = Array.isArray(localeFeatures) ? localeFeatures[fi] : undefined;
    return {
      ...f,
      tab: t(`how_it_works_page.${f.tabKey}` as any),
      items: f.items.map((item, ii) => {
        const locItem = locF?.items?.[ii];
        return { ...item, title: locItem?.title ?? item.title, desc: locItem?.desc ?? item.desc, badge: locItem?.badge ?? item.badge, extras: locItem?.extras ?? item.extras };
      }),
    };
  });
  const activeSection = FEATURES.find(f => f.id === activeTab) ?? FEATURES[0];

  return (
    <div className="min-h-screen bg-bg">

      {/* ── Nav ──────────────────────────────────────────────── */}
      <nav className="bg-surface border-b border-border sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
          <Link href="/" className="font-syne font-extrabold text-xl tracking-tight text-ink flex-shrink-0">
            Med<span className="text-red">Mind</span>
          </Link>
          <div className="hidden md:flex items-center gap-1">
            <Link href="/how-it-works" className="font-syne font-semibold text-sm text-ink px-3 py-2 border-b-2 border-ink">{t("how_it_works_page.nav_how")}</Link>
            <Link href="/articles"     className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">{t("how_it_works_page.nav_articles")}</Link>
            <Link href="/drugs"        className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">{t("how_it_works_page.nav_drugs")}</Link>
            <Link href="/pricing"      className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">{t("how_it_works_page.nav_pricing")}</Link>
          </div>
          <div className="flex items-center gap-2">
            <select value={locale} onChange={e => setLocale(e.target.value as any)}
              className="hidden sm:block text-xs font-syne border border-border rounded px-1.5 py-1 bg-bg text-ink focus:outline-none">
              {LANGS.map(l => <option key={l.value} value={l.value}>{l.flag}</option>)}
            </select>
            <Link href="/login" className="hidden sm:block font-syne font-semibold text-sm text-ink-2 hover:text-ink px-3 py-2">{t("how_it_works_page.nav_sign_in")}</Link>
            <Link href="/register" className="font-syne font-bold text-sm bg-ink text-white px-4 py-2 rounded hover:bg-red transition-colors whitespace-nowrap">{t("how_it_works_page.nav_register")} →</Link>
            <button onClick={() => setMenuOpen(v => !v)} className="md:hidden p-2 rounded text-ink-2 hover:text-ink">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {menuOpen
                  ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />}
              </svg>
            </button>
          </div>
        </div>
        {menuOpen && (
          <div className="md:hidden border-t border-border bg-surface px-4 py-3 space-y-1">
            {([
              [t("how_it_works_page.nav_how"), "/how-it-works"],
              [t("how_it_works_page.nav_articles"), "/articles"],
              [t("how_it_works_page.nav_drugs"), "/drugs"],
              [t("how_it_works_page.nav_pricing"), "/pricing"],
              [t("how_it_works_page.nav_sign_in"), "/login"],
            ] as [string, string][]).map(([label, href]) => (
              <Link key={href} href={href} onClick={() => setMenuOpen(false)}
                className="block font-syne font-semibold text-sm text-ink-2 hover:text-ink px-3 py-2.5 rounded-lg hover:bg-surface-2">
                {label}
              </Link>
            ))}
          </div>
        )}
      </nav>

      {/* ── Hero ─────────────────────────────────────────────── */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 pt-16 pb-12 text-center">
        <div className="inline-flex items-center gap-2 bg-surface border border-border px-3 py-1.5 rounded-full font-syne font-semibold text-xs text-ink-2 mb-6">
          <span className="w-2 h-2 rounded-full bg-blue animate-pulse inline-block" />
          {t("how_it_works_page.hero_badge")}
        </div>
        <h1 className="font-syne font-extrabold text-4xl sm:text-5xl md:text-6xl text-ink leading-tight tracking-tight mb-5">
          {t("how_it_works_page.hero_title_1")}<br />
          <span className="text-red">{t("how_it_works_page.hero_title_2")}</span>
        </h1>
        <p className="text-ink-2 text-base sm:text-lg max-w-2xl mx-auto leading-relaxed mb-8">
          {t("how_it_works_page.hero_desc")}
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-2xl mx-auto mb-10">
          {([["125+", t("how_it_works_page.stat_modules")], ["5,000+", t("how_it_works_page.stat_drugs")], ["2,400+", t("how_it_works_page.stat_images")], ["40+", t("how_it_works_page.stat_calculators")]] as [string, string][]).map(([n, l]) => (
            <div key={l} className="bg-surface border border-border rounded-xl p-4">
              <p className="font-syne font-black text-2xl text-ink">{n}</p>
              <p className="text-xs text-ink-3 font-syne">{l}</p>
            </div>
          ))}
        </div>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link href="/register" className="font-syne font-bold text-base bg-ink text-white px-10 py-3.5 rounded hover:bg-red transition-colors">
            {t("how_it_works_page.hero_cta_1")}
          </Link>
          <Link href="/pricing" className="font-syne font-semibold text-base border border-border-2 text-ink-2 px-10 py-3.5 rounded hover:border-ink hover:text-ink transition-colors">
            {t("how_it_works_page.hero_cta_2")}
          </Link>
        </div>
        <p className="text-ink-3 text-xs mt-3 font-syne">{t("how_it_works_page.hero_note_free")}</p>
      </section>

      {/* ── Feature showcase with tabs ────────────────────────── */}
      <section className="bg-surface border-y border-border py-14 sm:py-20">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink text-center mb-3">
            {t("how_it_works_page.features_title")}
          </h2>
          <p className="text-ink-3 text-center text-sm mb-10">
            {t("how_it_works_page.features_subtitle")}
          </p>

          {/* Tabs */}
          <div className="flex flex-wrap gap-2 justify-center mb-12">
            {FEATURES.map(f => (
              <button
                key={f.id}
                onClick={() => setActiveTab(f.id)}
                className={`font-syne font-semibold text-sm px-4 py-2 rounded-full transition-colors ${
                  activeTab === f.id
                    ? "bg-ink text-white"
                    : "bg-bg border border-border text-ink-2 hover:border-ink-2 hover:text-ink"
                }`}
              >
                {f.tab}
              </button>
            ))}
          </div>

          {/* Feature items */}
          <div className="space-y-20">
            {activeSection.items.map((item) => (
              <div
                key={item.title}
                className={`flex flex-col ${item.flip ? "lg:flex-row-reverse" : "lg:flex-row"} gap-10 lg:gap-16 items-center`}
              >
                {/* Text */}
                <div className="flex-1 min-w-0">
                  <span className="inline-block text-xs font-syne font-bold bg-amber-light text-amber px-3 py-1 rounded-full mb-4">
                    {item.badge}
                  </span>
                  <h3 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-4 leading-tight">
                    {item.title}
                  </h3>
                  <p className="text-ink-2 text-base leading-relaxed mb-6">{item.desc}</p>
                  <ul className="space-y-2.5">
                    {item.extras.map(e => (
                      <li key={e} className="flex items-start gap-2.5 text-sm text-ink-2">
                        <span className="text-green-2 mt-0.5 flex-shrink-0 font-bold">✓</span>
                        {e}
                      </li>
                    ))}
                  </ul>
                  <div className="mt-6">
                    <Link href="/register" className="inline-block font-syne font-semibold text-sm border border-border-2 text-ink-2 px-5 py-2.5 rounded hover:border-ink hover:text-ink transition-colors">
                      {t("how_it_works_page.try_free")}
                    </Link>
                  </div>
                </div>

                {/* Browser mockup */}
                <div className="w-full lg:w-[420px] shrink-0">
                  <Browser url={`/${activeSection.id}`}>
                    {item.mockup}
                  </Browser>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── All other features grid ──────────────────────────── */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
        <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink text-center mb-3">{t("how_it_works_page.features_more_title")}</h2>
        <p className="text-ink-3 text-center text-sm mb-10">{t("how_it_works_page.features_more_subtitle")}</p>
        <div className="grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {((): { icon: string; title: string; desc: string }[] => {
            const raw = t("how_it_works_page.mini_features");
            return Array.isArray(raw) ? raw as { icon: string; title: string; desc: string }[] : MINI_FEATURES;
          })().map(f => (
            <div key={f.title} className="bg-surface border border-border rounded-xl p-4 hover:border-border-2 transition-colors">
              <div className="text-2xl mb-2">{f.icon}</div>
              <h3 className="font-syne font-bold text-sm text-ink mb-1">{f.title}</h3>
              <p className="text-ink-3 text-xs leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Who it's for ─────────────────────────────────────── */}
      <section className="bg-surface border-y border-border py-14 sm:py-20">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink text-center mb-3">{t("how_it_works_page.roles_section_title")}</h2>
          <p className="text-ink-3 text-center text-sm mb-10">{t("how_it_works_page.roles_subtitle")}</p>
          <div className="grid sm:grid-cols-2 gap-5">
            {(Array.isArray(roles) ? roles : []).map(r => (
              <div key={r.role} className="bg-bg border border-border rounded-xl p-5 sm:p-6">
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-3xl">{r.icon}</span>
                  <h3 className="font-syne font-bold text-base sm:text-lg text-ink">{r.role}</h3>
                </div>
                <p className="text-ink-2 text-sm leading-relaxed mb-4">{r.description}</p>
                <ul className="space-y-2">
                  {r.features.map((f, j) => (
                    <li key={j} className="flex items-start gap-2 text-sm text-ink-3">
                      <span className="text-green-2 mt-0.5 flex-shrink-0">✓</span>{f}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 3-step quickstart ────────────────────────────────── */}
      <section className="max-w-4xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
        <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink text-center mb-3">{t("how_it_works_page.quickstart_title")}</h2>
        <p className="text-ink-3 text-center text-sm mb-12">{t("how_it_works_page.quickstart_subtitle")}</p>
        <div className="grid sm:grid-cols-3 gap-8">
          {((): { n: string; icon: string; title: string; desc: string }[] => {
            const raw = t("how_it_works_page.quickstart_steps");
            return Array.isArray(raw) ? raw as { n: string; icon: string; title: string; desc: string }[] : [
              { n: "01", icon: "📋", title: "Create free account", desc: "Sign up with email or Google. Choose your specialty and learning goal. No credit card required." },
              { n: "02", icon: "🎯", title: "Pick your first module", desc: "Browse 125+ modules by specialty. Start with an AI-recommended module or search for a specific topic." },
              { n: "03", icon: "🧠", title: "Learn with AI", desc: "Ask questions, work through cases, review flashcards. The AI adapts to your level and closes knowledge gaps systematically." },
            ];
          })().map(s => (
            <div key={s.n} className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 bg-surface border border-border rounded-2xl flex items-center justify-center text-3xl">
                {s.icon}
              </div>
              <div className="font-syne font-black text-3xl text-border-2 mb-2">{s.n}</div>
              <h3 className="font-syne font-bold text-base text-ink mb-2">{s.title}</h3>
              <p className="text-ink-3 text-sm leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Comparison table ─────────────────────────────────── */}
      <section className="bg-surface border-y border-border py-14 sm:py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6">
          <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink text-center mb-3">{t("how_it_works_page.cmp_title")}</h2>
          <p className="text-ink-3 text-center text-sm mb-10">{t("how_it_works_page.cmp_subtitle")}</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 pr-6 font-syne font-bold text-ink-2 w-44">{t("how_it_works_page.cmp_feature")}</th>
                  <th className="py-3 px-4 font-syne font-bold text-red text-center">{t("how_it_works_page.cmp_medmind")}</th>
                  <th className="py-3 px-4 font-syne font-bold text-ink-3 text-center">{t("how_it_works_page.cmp_chatbot")}</th>
                  <th className="py-3 px-4 font-syne font-bold text-ink-3 text-center">{t("how_it_works_page.cmp_anki")}</th>
                  <th className="py-3 px-4 font-syne font-bold text-ink-3 text-center">{t("how_it_works_page.cmp_textbook")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {(Array.isArray(cmpRows) ? cmpRows : []).map((row, i) => (
                  <tr key={i} className="hover:bg-surface-2 transition-colors">
                    <td className="py-3 pr-6 font-syne text-ink-2 text-xs sm:text-sm">{row[0]}</td>
                    {row.slice(1).map((v, j) => (
                      <td key={j} className={`py-3 px-4 text-center text-xs sm:text-sm ${j === 0 ? "text-green-2 font-bold" : "text-ink-3"}`}>{v}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* ── FAQ ──────────────────────────────────────────────── */}
      <section className="max-w-3xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
        <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink text-center mb-10">{t("how_it_works_page.faq_title")}</h2>
        <div className="space-y-3">
          {(Array.isArray(faq) ? faq : []).map((item, i) => (
            <div key={i} className="bg-surface border border-border rounded-xl overflow-hidden">
              <button
                onClick={() => setOpenFAQ(openFAQ === i ? null : i)}
                className="w-full flex items-center justify-between p-5 text-left hover:bg-surface-2 transition-colors"
              >
                <h3 className="font-syne font-bold text-sm sm:text-base text-ink pr-4">{item.q}</h3>
                <span className={`text-ink-3 text-xl transition-transform flex-shrink-0 ${openFAQ === i ? "rotate-45" : ""}`}>+</span>
              </button>
              {openFAQ === i && (
                <div className="px-5 pb-5 border-t border-border">
                  <p className="text-ink-2 text-sm leading-relaxed pt-4">{item.a}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* ── Final CTA ────────────────────────────────────────── */}
      <section className="bg-ink text-white">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-16 sm:py-20 text-center">
          <h2 className="font-syne font-extrabold text-3xl sm:text-4xl mb-4">{t("how_it_works_page.cta_title")}</h2>
          <p className="text-white/60 mb-8 text-base leading-relaxed">
            {t("how_it_works_page.cta_subtitle")}
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link href="/register" className="font-syne font-bold text-base bg-white text-ink px-10 py-4 rounded hover:bg-red hover:text-white transition-colors">
              {t("how_it_works_page.cta_btn")}
            </Link>
            <Link href="/pricing" className="font-syne font-semibold text-base border border-white/30 text-white/80 px-10 py-4 rounded hover:border-white hover:text-white transition-colors">
              {t("how_it_works_page.hero_cta_2")}
            </Link>
          </div>
          <p className="text-white/40 text-xs mt-4 font-syne">{t("how_it_works_page.hero_note_free")}</p>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────── */}
      <footer className="border-t border-border bg-surface">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="font-syne font-extrabold text-lg text-ink">
            Med<span className="text-red">Mind</span>
            <span className="font-normal text-ink-3 text-xs ml-2">AI-powered medical education</span>
          </div>
          <div className="flex gap-4 sm:gap-6 flex-wrap justify-center">
            {([
              [t("how_it_works_page.nav_how"), "/how-it-works"],
              [t("how_it_works_page.nav_articles"), "/articles"],
              [t("how_it_works_page.nav_drugs"), "/drugs"],
              [t("how_it_works_page.nav_pricing"), "/pricing"],
              [t("how_it_works_page.nav_register"), "/register"],
              [t("how_it_works_page.nav_sign_in"), "/login"],
            ] as [string, string][]).map(([label, href]) => (
              <Link key={href} href={href} className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">{label}</Link>
            ))}
          </div>
          <div className="text-ink-3 text-xs font-syne">{t("how_it_works_page.footer_copy")}</div>
        </div>
      </footer>
    </div>
  );
}
