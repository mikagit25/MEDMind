/**
 * AI Tutor screen — streaming SSE chat with Claude
 */
import { useState, useRef, useCallback } from 'react';
import { isOffline, getOfflineAIResponse } from '@/lib/offlineAI';
import {
  View, Text, ScrollView, TextInput, TouchableOpacity,
  StyleSheet, KeyboardAvoidingView, Platform, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as SecureStore from 'expo-secure-store';

interface Message { id: string; role: 'user' | 'assistant'; content: string; }

const COLORS = { bg: '#F5F0E8', ink: '#1A1A1A', ink2: '#6B6B6B', surface: '#FFFFFF', border: '#E8E3D9', blue: '#3B82F6', userBubble: '#1A1A1A', aiBubble: '#FFFFFF' };

const QUICK_PROMPTS = [
  'Explain the cardiac action potential',
  "What's the mechanism of beta blockers?",
  'Summarize heart failure management',
  'How does digoxin work?',
];

export default function AIScreen() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef<ScrollView>(null);
  const conversationId = useRef<string | null>(null);
  const abortRef = useRef<(() => void) | null>(null);

  const scrollToBottom = () => {
    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);
  };

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || streaming) return;
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: text.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setStreaming(true);
    scrollToBottom();

    const aiMsgId = (Date.now() + 1).toString();
    setMessages((prev) => [...prev, { id: aiMsgId, role: 'assistant', content: '' }]);

    const controller = new AbortController();
    abortRef.current = () => controller.abort();

    try {
      // Offline check — use canned response instead of hitting the network
      const offline = await isOffline();
      if (offline) {
        const { reply } = await getOfflineAIResponse(text.trim(), 'General Medicine', 'tutor');
        setMessages((prev) =>
          prev.map((m) => (m.id === aiMsgId ? { ...m, content: reply } : m))
        );
        setStreaming(false);
        scrollToBottom();
        return;
      }

      const token = await SecureStore.getItemAsync('medmind_access_token');
      const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

      const res = await fetch(`${BASE_URL}/ai/ask/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: text.trim(),
          conversation_id: conversationId.current ?? undefined,
          specialty: 'General Medicine',
          mode: 'tutor',
          search_pubmed: false,
        }),
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) throw new Error('No response body');

      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const event = JSON.parse(line.slice(6));
            if (event.type === 'meta') {
              conversationId.current = event.conversation_id;
            } else if (event.type === 'text') {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === aiMsgId ? { ...m, content: m.content + event.text } : m
                )
              );
              scrollToBottom();
            } else if (event.type === 'error') {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === aiMsgId ? { ...m, content: `⚠️ ${event.detail}` } : m
                )
              );
            }
          } catch {}
        }
      }
      setStreaming(false);
      scrollToBottom();
    } catch (err: any) {
      setStreaming(false);
      if (err?.name === 'AbortError') return; // user stopped — keep partial content
      setMessages((prev) =>
        prev.map((m) =>
          m.id === aiMsgId && m.content === '' ? { ...m, content: '⚠️ Failed to connect to AI.' } : m
        )
      );
    }
  }, [streaming]);

  const stopStreaming = () => {
    abortRef.current?.();
    setStreaming(false);
  };

  return (
    <SafeAreaView style={s.container}>
      <View style={s.header}>
        <Text style={s.headerTitle}>🤖 AI Tutor</Text>
        <Text style={s.headerSub}>Powered by Claude</Text>
      </View>

      <KeyboardAvoidingView
        style={s.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={90}
      >
        <ScrollView
          ref={scrollRef}
          style={s.messages}
          contentContainerStyle={s.messagesContent}
          keyboardShouldPersistTaps="handled"
        >
          {messages.length === 0 && (
            <View style={s.empty}>
              <Text style={s.emptyIcon}>💡</Text>
              <Text style={s.emptyTitle}>Ask me anything</Text>
              <Text style={s.emptySub}>Medical questions, case discussions, pharmacology — I'm here to help.</Text>
              <View style={s.quickPrompts}>
                {QUICK_PROMPTS.map((p) => (
                  <TouchableOpacity key={p} style={s.quickBtn} onPress={() => sendMessage(p)}>
                    <Text style={s.quickBtnText}>{p}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
          )}

          {messages.map((msg) => (
            <View
              key={msg.id}
              style={[s.bubble, msg.role === 'user' ? s.userBubble : s.aiBubble]}
            >
              {msg.role === 'assistant' && msg.content === '' && streaming ? (
                <ActivityIndicator size="small" color={COLORS.ink2} />
              ) : (
                <Text style={[s.bubbleText, msg.role === 'user' ? s.userText : s.aiText]}>
                  {msg.content}
                </Text>
              )}
            </View>
          ))}
        </ScrollView>

        <View style={s.inputBar}>
          <TextInput
            style={s.input}
            value={input}
            onChangeText={setInput}
            placeholder="Ask a medical question…"
            placeholderTextColor={COLORS.ink2}
            multiline
            maxLength={2000}
            onSubmitEditing={() => sendMessage(input)}
          />
          {streaming ? (
            <TouchableOpacity style={s.stopBtn} onPress={stopStreaming}>
              <Text style={s.stopIcon}>⏹</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity
              style={[s.sendBtn, !input.trim() && s.sendBtnDisabled]}
              onPress={() => sendMessage(input)}
              disabled={!input.trim()}
            >
              <Text style={s.sendIcon}>↑</Text>
            </TouchableOpacity>
          )}
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  flex: { flex: 1 },
  header: { paddingHorizontal: 20, paddingTop: 8, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: COLORS.border, backgroundColor: COLORS.bg },
  headerTitle: { fontSize: 18, fontWeight: '800', color: COLORS.ink },
  headerSub: { fontSize: 12, color: COLORS.ink2, marginTop: 2 },
  messages: { flex: 1 },
  messagesContent: { padding: 16, gap: 12 },
  bubble: { maxWidth: '85%', borderRadius: 16, padding: 12 },
  userBubble: { alignSelf: 'flex-end', backgroundColor: COLORS.userBubble },
  aiBubble: { alignSelf: 'flex-start', backgroundColor: COLORS.aiBubble, borderWidth: 1, borderColor: COLORS.border, shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 8, elevation: 1 },
  bubbleText: { fontSize: 15, lineHeight: 22 },
  userText: { color: '#FFF' },
  aiText: { color: COLORS.ink },
  empty: { alignItems: 'center', paddingVertical: 40 },
  emptyIcon: { fontSize: 48, marginBottom: 12 },
  emptyTitle: { fontSize: 20, fontWeight: '800', color: COLORS.ink, marginBottom: 8 },
  emptySub: { fontSize: 13, color: COLORS.ink2, textAlign: 'center', marginBottom: 24, paddingHorizontal: 20 },
  quickPrompts: { gap: 8, width: '100%' },
  quickBtn: { backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border, borderRadius: 10, padding: 12 },
  quickBtnText: { fontSize: 13, color: COLORS.ink, fontWeight: '500' },
  inputBar: { flexDirection: 'row', alignItems: 'flex-end', gap: 10, padding: 12, borderTopWidth: 1, borderTopColor: COLORS.border, backgroundColor: COLORS.bg },
  input: { flex: 1, backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border, borderRadius: 20, paddingHorizontal: 16, paddingVertical: 10, fontSize: 15, color: COLORS.ink, maxHeight: 100 },
  sendBtn: { width: 40, height: 40, borderRadius: 20, backgroundColor: COLORS.ink, justifyContent: 'center', alignItems: 'center' },
  sendBtnDisabled: { opacity: 0.3 },
  sendIcon: { color: '#FFF', fontSize: 20, fontWeight: '700' },
  stopBtn: { width: 40, height: 40, borderRadius: 20, backgroundColor: '#EF4444', justifyContent: 'center', alignItems: 'center' },
  stopIcon: { color: '#FFF', fontSize: 16 },
});
