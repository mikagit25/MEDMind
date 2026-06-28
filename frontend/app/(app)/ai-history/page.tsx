"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useT } from "@/lib/i18n";
import { aiApi, contentApi } from "@/lib/api";
import { MessageSquare, ChevronRight, X, User, Bot, Download } from "lucide-react";
import { API_URL } from "@/lib/api";

type Conversation = {
  id: string;
  title: string | null;
  specialty: string | null;
  mode: string;
  created_at: string;
  updated_at: string;
};

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  from_cache: boolean;
  created_at: string;
};

const MODE_LABEL: Record<string, string> = {
  tutor:          "Tutor",
  socratic:       "Socratic",
  quiz:           "Quiz",
  case:           "Case",
  exam:           "Exam",
  explain:        "Explain",
  patient:        "Patient",
  differential:   "Differential Dx",
  handout:        "Handout",
  analyze:        "Doc Analysis",
  second_opinion: "Second Opinion",
};

async function downloadConversationPDF(convId: string) {
  const token = localStorage.getItem("access_token") ?? "";
  const res = await fetch(`${API_URL}/ai/conversations/${convId}/export-pdf`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return;
  const blob = await res.blob();
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = `medmind_session_${convId.slice(0, 8)}.pdf`;
  a.click();
  URL.revokeObjectURL(url);
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { dateStyle: "medium" });
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString(undefined, { timeStyle: "short" });
}

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex gap-2 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center ${isUser ? "bg-primary/10" : "bg-surface border border-border"}`}>
        {isUser
          ? <User size={14} className="text-primary" strokeWidth={1.75} />
          : <Bot size={14} className="text-ink-2" strokeWidth={1.75} />}
      </div>
      <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${isUser ? "bg-primary text-white" : "bg-surface border border-border text-ink"}`}>
        <p className="whitespace-pre-wrap">{msg.content}</p>
        <p className={`text-xs mt-1 ${isUser ? "text-white/60" : "text-ink-3"}`}>{formatTime(msg.created_at)}</p>
      </div>
    </div>
  );
}

function ConversationModal({ conv, onClose, specialtyMap }: { conv: Conversation; onClose: () => void; specialtyMap: Record<string, string> }) {
  const t = useT();
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    aiApi.getMessages(conv.id)
      .then(setMessages)
      .catch(() => setMessages([]))
      .finally(() => setLoading(false));
  }, [conv.id]);

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-black/40">
      <div className="bg-white dark:bg-neutral-900 rounded-2xl w-full max-w-xl max-h-[80vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="min-w-0">
            <p className="font-syne font-semibold text-sm text-ink truncate">
              {conv.title ?? t("ai_history.untitled")}
            </p>
            <p className="text-xs text-ink-3">
              {MODE_LABEL[conv.mode] ?? conv.mode}
              {conv.specialty ? ` · ${specialtyMap[conv.specialty] ?? specialtyMap[conv.specialty?.toLowerCase()] ?? conv.specialty}` : ""}
              {" · "}{formatDate(conv.updated_at)}
            </p>
          </div>
          <button onClick={onClose} className="p-1.5 text-ink-3 hover:text-ink ml-3 flex-shrink-0">
            <X size={18} strokeWidth={1.75} />
          </button>
        </div>
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {loading ? (
            <p className="text-center text-ink-2 text-sm py-8">{t("ai_history.loading_messages")}</p>
          ) : messages.length === 0 ? (
            <p className="text-center text-ink-2 text-sm py-8">{t("ai_history.no_messages")}</p>
          ) : (
            messages.map(m => <MessageBubble key={m.id} msg={m} />)
          )}
        </div>
        {/* Footer */}
        <div className="p-4 border-t border-border flex items-center gap-3">
          <Link
            href={`/ai-tutor?conversation_id=${conv.id}`}
            className="flex-1 text-center text-sm font-semibold text-primary hover:underline"
            onClick={onClose}
          >
            {t("ai_history.resume")} →
          </Link>
          <button
            onClick={() => downloadConversationPDF(conv.id)}
            title="Download PDF"
            className="flex items-center gap-1.5 text-xs font-syne text-ink-3 hover:text-ink border border-border rounded-lg px-3 py-1.5 transition-colors flex-shrink-0"
          >
            <Download size={13} /> PDF
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AIHistoryPage() {
  const t = useT();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Conversation | null>(null);
  const [specialtyMap, setSpecialtyMap] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [data, specs] = await Promise.all([
        aiApi.getConversations(),
        contentApi.getSpecialties().catch(() => []),
      ]);
      setConversations(data);
      const map: Record<string, string> = {};
      for (const s of (specs as any[])) {
        if (s.code) map[s.code] = s.name;
        if (s.id) map[s.id] = s.name;
        if (s.name) map[s.name.toLowerCase()] = s.name;
      }
      setSpecialtyMap(map);
    } catch {
      setConversations([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <>
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-xl">
            <MessageSquare size={22} className="text-primary" strokeWidth={1.75} />
          </div>
          <div>
            <h1 className="font-syne font-bold text-xl text-ink">{t("ai_history.title")}</h1>
            <p className="text-sm text-ink-2">{t("ai_history.subtitle")}</p>
          </div>
        </div>

        <Link href="/ai-tutor" className="text-sm text-primary hover:underline">
          {t("ai_history.start_new")} →
        </Link>

        {/* List */}
        {loading ? (
          <div className="text-center py-16 text-ink-2">{t("ai_history.loading")}</div>
        ) : conversations.length === 0 ? (
          <div className="text-center py-16 space-y-2">
            <p className="text-ink-2">{t("ai_history.empty")}</p>
            <Link href="/ai-tutor" className="text-sm text-primary hover:underline">
              {t("ai_history.go_to_tutor")} →
            </Link>
          </div>
        ) : (
          <div className="space-y-2">
            {conversations.map(conv => (
              <button
                key={conv.id}
                onClick={() => setSelected(conv)}
                className="w-full flex items-center gap-3 bg-surface border border-border rounded-xl p-4 text-left hover:border-primary/50 transition-colors group"
              >
                <div className="p-2 bg-primary/10 rounded-lg flex-shrink-0">
                  <MessageSquare size={16} className="text-primary" strokeWidth={1.75} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-syne font-medium text-sm text-ink truncate">
                    {conv.title ?? t("ai_history.untitled")}
                  </p>
                  <p className="text-xs text-ink-3 mt-0.5">
                    {MODE_LABEL[conv.mode] ?? conv.mode}
                    {conv.specialty ? ` · ${specialtyMap[conv.specialty] ?? specialtyMap[conv.specialty?.toLowerCase()] ?? conv.specialty}` : ""}
                    {" · "}{formatDate(conv.updated_at)}
                  </p>
                </div>
                <ChevronRight size={16} className="text-ink-3 group-hover:text-primary flex-shrink-0 transition-colors" strokeWidth={1.75} />
              </button>
            ))}
          </div>
        )}
      </div>

      {selected && (
        <ConversationModal conv={selected} onClose={() => setSelected(null)} specialtyMap={specialtyMap} />
      )}
    </>
  );
}
