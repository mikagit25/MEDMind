/**
 * AI Tutor screen — streaming SSE chat with Claude + Voice mode (V5 Phase 7.3)
 *
 * TTS: expo-speech  — native device TTS, auto-speaks AI responses in voice mode.
 * STT: expo-speech-recognition — confirmation step before sending (medical safety).
 */
import { useState, useRef, useCallback, useEffect } from 'react';
import { isOffline, getOfflineAIResponse } from '@/lib/offlineAI';
import {
  View, Text, ScrollView, TextInput, TouchableOpacity,
  StyleSheet, KeyboardAvoidingView, Platform, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as SecureStore from 'expo-secure-store';
import * as Speech from 'expo-speech';
import {
  ExpoSpeechRecognitionModule,
  useSpeechRecognitionEvent,
} from 'expo-speech-recognition';

interface Message { id: string; role: 'user' | 'assistant'; content: string; }

const COLORS = {
  bg: '#F5F0E8', ink: '#1A1A1A', ink2: '#6B6B6B',
  surface: '#FFFFFF', border: '#E8E3D9',
  blue: '#3B82F6', red: '#C0392B',
  userBubble: '#1A1A1A', aiBubble: '#FFFFFF',
};

const QUICK_PROMPTS = [
  'Explain the cardiac action potential',
  "What's the mechanism of beta blockers?",
  'Summarize heart failure management',
  'How does digoxin work?',
];

export default function AIScreen() {
  const [messages, setMessages]         = useState<Message[]>([]);
  const [input, setInput]               = useState('');
  const [streaming, setStreaming]       = useState(false);
  const [voiceMode, setVoiceMode]       = useState(false);
  const [listening, setListening]       = useState(false);
  const [pendingVoice, setPendingVoice] = useState<string | null>(null);
  const [sttSupported, setSttSupported] = useState(true);

  const scrollRef               = useRef<ScrollView>(null);
  const conversationId          = useRef<string | null>(null);
  const abortRef                = useRef<(() => void) | null>(null);
  const lastAssistantContent    = useRef('');
  const voiceModeRef            = useRef(voiceMode);

  useEffect(() => { voiceModeRef.current = voiceMode; }, [voiceMode]);

  // Check STT availability on mount
  useEffect(() => {
    ExpoSpeechRecognitionModule.isRecognitionAvailable()
      .then((ok: boolean) => setSttSupported(ok))
      .catch(() => setSttSupported(false));
  }, []);

  // STT event listeners
  useSpeechRecognitionEvent('result', (event: any) => {
    const transcript = event.results?.[event.resultIndex ?? 0]?.[0]?.transcript ?? '';
    if (transcript) setPendingVoice(transcript);
  });
  useSpeechRecognitionEvent('end', () => setListening(false));
  useSpeechRecognitionEvent('error', () => setListening(false));

  const scrollToBottom = () => {
    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);
  };

  const startListening = async () => {
    try {
      const perm = await ExpoSpeechRecognitionModule.requestPermissionsAsync();
      if (!perm.granted) return;
      setListening(true);
      setPendingVoice(null);
      ExpoSpeechRecognitionModule.start({ lang: 'en-US', interimResults: false });
    } catch {
      setListening(false);
    }
  };

  const stopListening = () => {
    try { ExpoSpeechRecognitionModule.stop(); } catch {}
    setListening(false);
  };

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || streaming) return;
    setPendingVoice(null);
    lastAssistantContent.current = '';

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
      const offline = await isOffline();
      if (offline) {
        const { reply } = await getOfflineAIResponse(text.trim(), 'General Medicine', 'tutor');
        setMessages((prev) =>
          prev.map((m) => (m.id === aiMsgId ? { ...m, content: reply } : m))
        );
        lastAssistantContent.current = reply;
        setStreaming(false);
        scrollToBottom();
        if (voiceModeRef.current) Speech.speak(reply.slice(0, 500));
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

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

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
                prev.map((m) => {
                  if (m.id !== aiMsgId) return m;
                  const next = m.content + event.text;
                  lastAssistantContent.current = next;
                  return { ...m, content: next };
                })
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
    } catch (err: any) {
      if (err?.name === 'AbortError') return;
      setMessages((prev) =>
        prev.map((m) =>
          m.id === aiMsgId && m.content === '' ? { ...m, content: '⚠️ Failed to connect to AI.' } : m
        )
      );
    } finally {
      setStreaming(false);
      scrollToBottom();
      if (voiceModeRef.current && lastAssistantContent.current) {
        Speech.speak(lastAssistantContent.current.slice(0, 500), { language: 'en-US' });
      }
    }
  }, [streaming]);

  const stopStreaming = () => {
    abortRef.current?.();
    setStreaming(false);
  };

  return (
    <SafeAreaView style={s.container}>
      <View style={s.header}>
        <View>
          <Text style={s.headerTitle}>🤖 AI Tutor</Text>
          <Text style={s.headerSub}>Powered by Claude</Text>
        </View>
        {/* Voice mode toggle */}
        <TouchableOpacity
          style={[s.voiceToggle, voiceMode && s.voiceToggleActive]}
          onPress={() => {
            if (voiceMode) Speech.stop();
            setVoiceMode((v) => !v);
          }}
        >
          <Text style={[s.voiceToggleText, voiceMode && s.voiceToggleTextActive]}>
            {voiceMode ? '🔊 ON' : '🔇 Voice'}
          </Text>
        </TouchableOpacity>
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

        {/* Voice confirmation banner */}
        {pendingVoice && (
          <View style={s.voiceBanner}>
            <Text style={s.voiceBannerLabel}>🎙️ Heard:</Text>
            <Text style={s.voiceBannerText} numberOfLines={2}>{pendingVoice}</Text>
            <View style={s.voiceBannerActions}>
              <TouchableOpacity
                style={s.voiceBannerEdit}
                onPress={() => { setInput(pendingVoice); setPendingVoice(null); }}
              >
                <Text style={s.voiceBannerEditText}>Edit</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={s.voiceBannerSend}
                onPress={() => sendMessage(pendingVoice)}
              >
                <Text style={s.voiceBannerSendText}>Send</Text>
              </TouchableOpacity>
              <TouchableOpacity onPress={() => setPendingVoice(null)}>
                <Text style={s.voiceBannerDismiss}>✕</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        <View style={s.inputBar}>
          {/* Mic button — only if STT is supported */}
          {sttSupported && (
            <TouchableOpacity
              style={[s.micBtn, listening && s.micBtnActive]}
              onPress={listening ? stopListening : startListening}
              disabled={streaming}
            >
              <Text style={s.micIcon}>{listening ? '⏹' : '🎙️'}</Text>
            </TouchableOpacity>
          )}

          <TextInput
            style={s.input}
            value={input}
            onChangeText={setInput}
            placeholder={listening ? 'Listening…' : 'Ask a medical question…'}
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
  container:    { flex: 1, backgroundColor: COLORS.bg },
  flex:         { flex: 1 },
  header:       { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 20, paddingTop: 8, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: COLORS.border, backgroundColor: COLORS.bg },
  headerTitle:  { fontSize: 18, fontWeight: '800', color: COLORS.ink },
  headerSub:    { fontSize: 12, color: COLORS.ink2, marginTop: 2 },
  voiceToggle:  { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20, borderWidth: 1, borderColor: COLORS.border, backgroundColor: COLORS.surface },
  voiceToggleActive: { backgroundColor: COLORS.blue, borderColor: COLORS.blue },
  voiceToggleText:   { fontSize: 12, fontWeight: '600', color: COLORS.ink2 },
  voiceToggleTextActive: { color: '#fff' },
  messages:     { flex: 1 },
  messagesContent: { padding: 16, gap: 12 },
  bubble:       { maxWidth: '85%', borderRadius: 16, padding: 12 },
  userBubble:   { alignSelf: 'flex-end', backgroundColor: COLORS.userBubble },
  aiBubble:     { alignSelf: 'flex-start', backgroundColor: COLORS.aiBubble, borderWidth: 1, borderColor: COLORS.border, shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 8, elevation: 1 },
  bubbleText:   { fontSize: 15, lineHeight: 22 },
  userText:     { color: '#FFF' },
  aiText:       { color: COLORS.ink },
  empty:        { alignItems: 'center', paddingVertical: 40 },
  emptyIcon:    { fontSize: 48, marginBottom: 12 },
  emptyTitle:   { fontSize: 20, fontWeight: '800', color: COLORS.ink, marginBottom: 8 },
  emptySub:     { fontSize: 13, color: COLORS.ink2, textAlign: 'center', marginBottom: 24, paddingHorizontal: 20 },
  quickPrompts: { gap: 8, width: '100%' },
  quickBtn:     { backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border, borderRadius: 10, padding: 12 },
  quickBtnText: { fontSize: 13, color: COLORS.ink, fontWeight: '500' },
  // Voice confirmation banner
  voiceBanner:  { margin: 10, padding: 12, backgroundColor: '#EFF6FF', borderRadius: 12, borderWidth: 1, borderColor: '#BFDBFE' },
  voiceBannerLabel: { fontSize: 11, color: '#6B7280', marginBottom: 4 },
  voiceBannerText:  { fontSize: 14, color: COLORS.ink, fontWeight: '500', marginBottom: 8 },
  voiceBannerActions: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  voiceBannerEdit:    { paddingHorizontal: 12, paddingVertical: 5, borderRadius: 8, borderWidth: 1, borderColor: COLORS.border },
  voiceBannerEditText: { fontSize: 13, color: COLORS.ink2 },
  voiceBannerSend:    { paddingHorizontal: 12, paddingVertical: 5, borderRadius: 8, backgroundColor: COLORS.ink },
  voiceBannerSendText: { fontSize: 13, color: '#fff', fontWeight: '600' },
  voiceBannerDismiss:  { fontSize: 18, color: COLORS.ink2, paddingHorizontal: 4 },
  // Input bar
  inputBar:     { flexDirection: 'row', alignItems: 'flex-end', gap: 8, padding: 12, borderTopWidth: 1, borderTopColor: COLORS.border, backgroundColor: COLORS.bg },
  micBtn:       { width: 40, height: 40, borderRadius: 20, borderWidth: 1, borderColor: COLORS.border, backgroundColor: COLORS.surface, justifyContent: 'center', alignItems: 'center' },
  micBtnActive: { backgroundColor: '#FEE2E2', borderColor: COLORS.red },
  micIcon:      { fontSize: 18 },
  input:        { flex: 1, backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border, borderRadius: 20, paddingHorizontal: 16, paddingVertical: 10, fontSize: 15, color: COLORS.ink, maxHeight: 100 },
  sendBtn:      { width: 40, height: 40, borderRadius: 20, backgroundColor: COLORS.ink, justifyContent: 'center', alignItems: 'center' },
  sendBtnDisabled: { opacity: 0.3 },
  sendIcon:     { color: '#FFF', fontSize: 20, fontWeight: '700' },
  stopBtn:      { width: 40, height: 40, borderRadius: 20, backgroundColor: '#EF4444', justifyContent: 'center', alignItems: 'center' },
  stopIcon:     { color: '#FFF', fontSize: 16 },
});
