"use client";

import { useState } from "react";
import { useT } from "@/lib/i18n";
import { fhirApi } from "@/lib/api";
import { Download, FileJson, ClipboardList, User, ExternalLink, type LucideIcon } from "lucide-react";

type ExportStatus = "idle" | "loading" | "done" | "error";

function downloadJson(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function ExportCard({
  icon: Icon,
  title,
  description,
  filename,
  fetcher,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  filename: string;
  fetcher: () => Promise<unknown>;
}) {
  const t = useT();
  const [status, setStatus] = useState<ExportStatus>("idle");

  async function handleExport() {
    setStatus("loading");
    try {
      const data = await fetcher();
      downloadJson(data, filename);
      setStatus("done");
      setTimeout(() => setStatus("idle"), 3000);
    } catch {
      setStatus("error");
      setTimeout(() => setStatus("idle"), 4000);
    }
  }

  return (
    <div className="bg-surface border border-border rounded-xl p-5 flex items-start gap-4">
      <div className="p-2.5 bg-primary/10 rounded-xl flex-shrink-0">
        <Icon size={20} className="text-primary" strokeWidth={1.75} />
      </div>
      <div className="flex-1 min-w-0 space-y-1">
        <p className="font-syne font-semibold text-sm text-ink">{title}</p>
        <p className="text-xs text-ink-2 leading-relaxed">{description}</p>
        {status === "error" && (
          <p className="text-xs text-red-500">{t("fhir_export.error")}</p>
        )}
      </div>
      <button
        onClick={handleExport}
        disabled={status === "loading" || status === "done"}
        className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold flex-shrink-0 transition-colors disabled:cursor-not-allowed ${
          status === "done"
            ? "bg-green-100 text-green-700"
            : status === "error"
              ? "bg-red-50 text-red-600 border border-red-200"
              : "border border-border text-ink-2 hover:border-primary hover:text-primary disabled:opacity-60"
        }`}
      >
        <Download size={13} strokeWidth={2} />
        {status === "loading"
          ? t("fhir_export.downloading")
          : status === "done"
            ? t("fhir_export.downloaded")
            : t("fhir_export.download")}
      </button>
    </div>
  );
}

export default function FhirExportPage() {
  const t = useT();

  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-primary/10 rounded-xl">
            <FileJson size={22} className="text-primary" strokeWidth={1.75} />
          </div>
          <h1 className="font-syne font-bold text-xl text-ink">{t("fhir_export.title")}</h1>
        </div>
        <p className="text-sm text-ink-2 leading-relaxed">{t("fhir_export.subtitle")}</p>
      </div>

      {/* What is FHIR info box */}
      <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 space-y-2">
        <p className="text-sm font-semibold text-blue-800">{t("fhir_export.what_is_fhir")}</p>
        <p className="text-xs text-blue-700 leading-relaxed">{t("fhir_export.fhir_description")}</p>
        <a
          href="https://hl7.org/fhir/R4/"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
        >
          HL7 FHIR R4 <ExternalLink size={11} />
        </a>
      </div>

      {/* Export options */}
      <div className="space-y-3">
        <h2 className="font-syne font-semibold text-sm text-ink-2 uppercase tracking-wide">
          {t("fhir_export.export_options")}
        </h2>

        <ExportCard
          icon={FileJson}
          title={t("fhir_export.bundle_title")}
          description={t("fhir_export.bundle_description")}
          filename={`medmind-fhir-bundle-${today}.json`}
          fetcher={fhirApi.bundle}
        />

        <ExportCard
          icon={ClipboardList}
          title={t("fhir_export.diagnostic_report_title")}
          description={t("fhir_export.diagnostic_report_description")}
          filename={`medmind-cpd-report-${today}.json`}
          fetcher={fhirApi.diagnosticReport}
        />

        <ExportCard
          icon={User}
          title={t("fhir_export.practitioner_title")}
          description={t("fhir_export.practitioner_description")}
          filename={`medmind-practitioner-${today}.json`}
          fetcher={fhirApi.practitioner}
        />
      </div>

      {/* Disclaimer */}
      <p className="text-xs text-ink-3 leading-relaxed">{t("fhir_export.disclaimer")}</p>
    </div>
  );
}
