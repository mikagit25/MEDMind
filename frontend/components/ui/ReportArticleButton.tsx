"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

type ProblemType = "factual_error" | "outdated" | "missing_source" | "wrong_translation" | "other";

const LABELS: Record<string, Record<string, string>> = {
  en: {
    trigger: "Report inaccuracy",
    title: "Report an inaccuracy",
    subtitle: "Help us improve — tell us what's wrong with this content.",
    problem_label: "What's the problem?",
    factual_error: "Factual error",
    outdated: "Outdated information",
    missing_source: "Missing or wrong source",
    wrong_translation: "Wrong translation",
    other: "Other",
    comment_label: "Details (optional)",
    comment_placeholder: "Describe the error or inaccuracy…",
    email_label: "Your email (optional, for follow-up)",
    email_placeholder: "email@example.com",
    submit: "Submit report",
    submitting: "Sending…",
    success_title: "Thank you!",
    success_body: "Your report has been received and will be reviewed by our editorial team.",
    cancel: "Cancel",
    close: "Close",
  },
  ru: {
    trigger: "Сообщить о неточности",
    title: "Сообщить о неточности",
    subtitle: "Помогите нам улучшить контент — опишите проблему.",
    problem_label: "В чём проблема?",
    factual_error: "Фактическая ошибка",
    outdated: "Устаревшая информация",
    missing_source: "Нет или неверный источник",
    wrong_translation: "Ошибка перевода",
    other: "Другое",
    comment_label: "Подробности (необязательно)",
    comment_placeholder: "Опишите ошибку или неточность…",
    email_label: "Ваш email (необязательно)",
    email_placeholder: "email@example.com",
    submit: "Отправить",
    submitting: "Отправка…",
    success_title: "Спасибо!",
    success_body: "Ваше сообщение получено и будет рассмотрено редакцией.",
    cancel: "Отмена",
    close: "Закрыть",
  },
  ar: {
    trigger: "الإبلاغ عن خطأ",
    title: "الإبلاغ عن خطأ",
    subtitle: "ساعدنا في تحسين المحتوى — أخبرنا بالمشكلة.",
    problem_label: "ما هي المشكلة؟",
    factual_error: "خطأ في الحقائق",
    outdated: "معلومات قديمة",
    missing_source: "مصدر مفقود أو خاطئ",
    wrong_translation: "خطأ في الترجمة",
    other: "أخرى",
    comment_label: "التفاصيل (اختياري)",
    comment_placeholder: "صف الخطأ أو عدم الدقة…",
    email_label: "بريدك الإلكتروني (اختياري)",
    email_placeholder: "email@example.com",
    submit: "إرسال التقرير",
    submitting: "جارٍ الإرسال…",
    success_title: "شكراً!",
    success_body: "تم استلام تقريرك وسيتم مراجعته من قِبل فريق التحرير.",
    cancel: "إلغاء",
    close: "إغلاق",
  },
  de: {
    trigger: "Ungenauigkeit melden",
    title: "Ungenauigkeit melden",
    subtitle: "Helfen Sie uns, den Inhalt zu verbessern — beschreiben Sie das Problem.",
    problem_label: "Was ist das Problem?",
    factual_error: "Faktenfehler",
    outdated: "Veraltete Informationen",
    missing_source: "Fehlende oder falsche Quelle",
    wrong_translation: "Übersetzungsfehler",
    other: "Sonstiges",
    comment_label: "Details (optional)",
    comment_placeholder: "Beschreiben Sie den Fehler…",
    email_label: "Ihre E-Mail (optional)",
    email_placeholder: "email@example.com",
    submit: "Bericht senden",
    submitting: "Wird gesendet…",
    success_title: "Danke!",
    success_body: "Ihr Bericht wurde empfangen und wird von unserem Redaktionsteam geprüft.",
    cancel: "Abbrechen",
    close: "Schließen",
  },
  fr: {
    trigger: "Signaler une inexactitude",
    title: "Signaler une inexactitude",
    subtitle: "Aidez-nous à améliorer le contenu — décrivez le problème.",
    problem_label: "Quel est le problème ?",
    factual_error: "Erreur factuelle",
    outdated: "Information obsolète",
    missing_source: "Source manquante ou incorrecte",
    wrong_translation: "Erreur de traduction",
    other: "Autre",
    comment_label: "Détails (facultatif)",
    comment_placeholder: "Décrivez l'erreur ou l'inexactitude…",
    email_label: "Votre email (facultatif)",
    email_placeholder: "email@example.com",
    submit: "Envoyer le signalement",
    submitting: "Envoi en cours…",
    success_title: "Merci !",
    success_body: "Votre signalement a été reçu et sera examiné par notre équipe éditoriale.",
    cancel: "Annuler",
    close: "Fermer",
  },
  es: {
    trigger: "Reportar inexactitud",
    title: "Reportar una inexactitud",
    subtitle: "Ayúdanos a mejorar el contenido — describe el problema.",
    problem_label: "¿Cuál es el problema?",
    factual_error: "Error factual",
    outdated: "Información desactualizada",
    missing_source: "Fuente faltante o incorrecta",
    wrong_translation: "Error de traducción",
    other: "Otro",
    comment_label: "Detalles (opcional)",
    comment_placeholder: "Describe el error o la inexactitud…",
    email_label: "Tu email (opcional)",
    email_placeholder: "email@example.com",
    submit: "Enviar reporte",
    submitting: "Enviando…",
    success_title: "¡Gracias!",
    success_body: "Tu reporte fue recibido y será revisado por nuestro equipo editorial.",
    cancel: "Cancelar",
    close: "Cerrar",
  },
  tr: {
    trigger: "Yanlışlık bildirin",
    title: "Yanlışlık bildirin",
    subtitle: "İçeriği iyileştirmemize yardımcı olun — sorunu açıklayın.",
    problem_label: "Sorun nedir?",
    factual_error: "Gerçek hatası",
    outdated: "Güncel olmayan bilgi",
    missing_source: "Eksik veya yanlış kaynak",
    wrong_translation: "Çeviri hatası",
    other: "Diğer",
    comment_label: "Ayrıntılar (isteğe bağlı)",
    comment_placeholder: "Hatayı veya yanlışlığı açıklayın…",
    email_label: "E-postanız (isteğe bağlı)",
    email_placeholder: "email@example.com",
    submit: "Rapor gönder",
    submitting: "Gönderiliyor…",
    success_title: "Teşekkürler!",
    success_body: "Raporunuz alındı ve editoryal ekibimiz tarafından incelenecek.",
    cancel: "İptal",
    close: "Kapat",
  },
};

const PROBLEM_TYPES: ProblemType[] = [
  "factual_error",
  "outdated",
  "missing_source",
  "wrong_translation",
  "other",
];

export function ReportArticleButton({
  contentType,
  contentId,
  locale = "en",
}: {
  contentType: "article" | "news";
  contentId: string;
  locale?: string;
}) {
  const t = LABELS[locale] ?? LABELS.en;
  const [open, setOpen] = useState(false);
  const [problem, setProblem] = useState<ProblemType>("factual_error");
  const [comment, setComment] = useState("");
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "submitting" | "success" | "error">("idle");

  async function submit() {
    setState("submitting");
    try {
      const res = await fetch(`${API_URL}/articles/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content_type: contentType,
          content_id: contentId,
          problem_type: problem,
          comment: comment.trim() || null,
          reporter_email: email.trim() || null,
        }),
      });
      if (!res.ok) throw new Error("Server error");
      setState("success");
    } catch {
      setState("error");
    }
  }

  function close() {
    setOpen(false);
    setTimeout(() => {
      setState("idle");
      setProblem("factual_error");
      setComment("");
      setEmail("");
    }, 300);
  }

  const dir = locale === "ar" ? "rtl" : "ltr";

  return (
    <>
      {/* Trigger */}
      <button
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1.5 text-xs font-serif text-ink-3 hover:text-amber transition-colors group"
        aria-label={t.trigger}
      >
        <svg className="w-3.5 h-3.5 flex-shrink-0 group-hover:text-amber transition-colors" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path strokeLinecap="round" strokeLinejoin="round" d="M8 2v7m0 3v.5M2.5 13.5h11l-5.5-11-5.5 11z" />
        </svg>
        {t.trigger}
      </button>

      {/* Backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-4"
          onClick={(e) => { if (e.target === e.currentTarget) close(); }}
          role="dialog"
          aria-modal="true"
        >
          {/* Modal */}
          <div
            className="bg-bg w-full sm:max-w-md rounded-t-2xl sm:rounded-2xl border border-border shadow-xl overflow-hidden"
            dir={dir}
          >
            {/* Header */}
            <div className="flex items-start justify-between px-5 pt-5 pb-3 border-b border-border">
              <div>
                <div className="font-syne font-bold text-base text-ink">{t.title}</div>
                <div className="font-serif text-xs text-ink-3 mt-0.5">{t.subtitle}</div>
              </div>
              <button
                onClick={close}
                className="ml-3 text-ink-3 hover:text-ink transition-colors flex-shrink-0 mt-0.5"
                aria-label="Close"
              >
                <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" d="M3 3l10 10M13 3L3 13" />
                </svg>
              </button>
            </div>

            {state === "success" ? (
              <div className="px-5 py-8 text-center">
                <div className="w-12 h-12 rounded-full bg-green-light border border-green/20 flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6 text-green" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 10l3.5 3.5L15 7" />
                  </svg>
                </div>
                <div className="font-syne font-bold text-base text-ink mb-1">{t.success_title}</div>
                <div className="font-serif text-sm text-ink-2 leading-relaxed">{t.success_body}</div>
                <button
                  onClick={close}
                  className="mt-5 px-5 py-2 bg-ink text-white font-syne font-semibold text-sm rounded-lg hover:bg-ink/90 transition-colors"
                >
                  {t.close}
                </button>
              </div>
            ) : (
              <div className="px-5 pt-4 pb-5 space-y-4">
                {/* Problem type */}
                <fieldset>
                  <legend className="font-syne font-semibold text-xs text-ink-2 uppercase tracking-wider mb-2">
                    {t.problem_label}
                  </legend>
                  <div className="space-y-1.5">
                    {PROBLEM_TYPES.map((type) => (
                      <label
                        key={type}
                        className={`flex items-center gap-2.5 px-3 py-2 rounded-lg border cursor-pointer transition-colors ${
                          problem === type
                            ? "border-ink bg-surface-2"
                            : "border-border hover:border-ink-3"
                        }`}
                      >
                        <input
                          type="radio"
                          name="problem"
                          value={type}
                          checked={problem === type}
                          onChange={() => setProblem(type)}
                          className="accent-ink w-3.5 h-3.5 flex-shrink-0"
                        />
                        <span className="font-serif text-sm text-ink">{t[type]}</span>
                      </label>
                    ))}
                  </div>
                </fieldset>

                {/* Comment */}
                <div>
                  <label className="font-syne font-semibold text-xs text-ink-2 uppercase tracking-wider block mb-1.5">
                    {t.comment_label}
                  </label>
                  <textarea
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder={t.comment_placeholder}
                    rows={3}
                    maxLength={2000}
                    className="w-full border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-bg placeholder:text-ink-3 focus:outline-none focus:border-ink resize-none"
                  />
                </div>

                {/* Email */}
                <div>
                  <label className="font-syne font-semibold text-xs text-ink-2 uppercase tracking-wider block mb-1.5">
                    {t.email_label}
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder={t.email_placeholder}
                    className="w-full border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-bg placeholder:text-ink-3 focus:outline-none focus:border-ink"
                  />
                </div>

                {state === "error" && (
                  <p className="font-serif text-xs text-red">Something went wrong. Please try again.</p>
                )}

                {/* Actions */}
                <div className="flex gap-2 pt-1">
                  <button
                    onClick={close}
                    className="flex-1 py-2 border border-border rounded-lg font-syne font-semibold text-sm text-ink-2 hover:border-ink hover:text-ink transition-colors"
                  >
                    {t.cancel}
                  </button>
                  <button
                    onClick={submit}
                    disabled={state === "submitting"}
                    className="flex-1 py-2 bg-ink text-white font-syne font-semibold text-sm rounded-lg hover:bg-ink/90 transition-colors disabled:opacity-60"
                  >
                    {state === "submitting" ? t.submitting : t.submit}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
