/**
 * Flashcards screen — SM-2 spaced repetition with offline support
 */
import { useEffect, useState, useRef } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, ActivityIndicator,
  Animated, ScrollView, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { progressApi, contentApi } from '@/lib/api';
import { db, syncFlashcards, pushPendingReviews } from '@/lib/database';
import { FlashcardModel } from '@/lib/models';

interface Card { id: string; front: string; back: string; }

const COLORS = { bg: '#F5F0E8', ink: '#1A1A1A', ink2: '#6B6B6B', surface: '#FFFFFF', border: '#E8E3D9', green: '#22C55E', amber: '#F59E0B', red: '#EF4444', blue: '#3B82F6' };

const QUALITY_LABELS = [
  { q: 0, label: 'Blackout', color: COLORS.red, emoji: '💀' },
  { q: 1, label: 'Wrong', color: '#F97316', emoji: '😕' },
  { q: 3, label: 'Hard', color: COLORS.amber, emoji: '😬' },
  { q: 4, label: 'Good', color: '#84CC16', emoji: '🙂' },
  { q: 5, label: 'Easy', color: COLORS.green, emoji: '🚀' },
];

export default function FlashcardsScreen() {
  const [cards, setCards] = useState<Card[]>([]);
  const [idx, setIdx] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(true);
  const [offlineMode, setOfflineMode] = useState(false);
  const flipAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    loadCards();
  }, []);

  const loadCards = async () => {
    setLoading(true);
    try {
      // Try online first
      const res = await progressApi.getDueFlashcards();
      setCards(res.data.map((c: any) => ({ id: c.id, front: c.question, back: c.answer })));
      setOfflineMode(false);
    } catch {
      // Fall back to local DB
      const local = await db.get<FlashcardModel>('flashcards')
        .query()
        .fetch()
        .then((all) => all.filter((f) => new Date(f.dueDate) <= new Date()));
      if (local.length > 0) {
        setCards(local.map((f) => ({ id: f.remoteId, front: f.front, back: f.back })));
        setOfflineMode(true);
      } else {
        setCards([]);
      }
    } finally {
      setLoading(false);
    }
  };

  const flipCard = () => {
    if (flipped) return;
    Animated.spring(flipAnim, { toValue: 1, useNativeDriver: true }).start();
    setFlipped(true);
  };

  const handleQuality = async (quality: number) => {
    const card = cards[idx];
    if (offlineMode) {
      // Queue for later sync
      const local = await db.get<FlashcardModel>('flashcards')
        .query()
        .fetch()
        .then((all) => all.find((f) => f.remoteId === card.id));
      if (local) {
        await db.write(async () => {
          await local.update((f) => {
            f.pendingReview = true;
            f.pendingQuality = quality;
          });
        });
      }
    } else {
      try {
        await progressApi.reviewFlashcard(card.id, quality);
      } catch {
        // Queue offline
        const local = await db.get<FlashcardModel>('flashcards')
          .query()
          .fetch()
          .then((all) => all.find((f) => f.remoteId === card.id));
        if (local) {
          await db.write(async () => {
            await local.update((f) => {
              f.pendingReview = true;
              f.pendingQuality = quality;
            });
          });
        }
      }
    }

    // Next card
    flipAnim.setValue(0);
    setFlipped(false);
    if (idx + 1 >= cards.length) {
      setDone(true);
      pushPendingReviews().catch(() => {});
    } else {
      setIdx((i) => i + 1);
    }
  };

  const frontInterp = flipAnim.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '90deg'] });
  const backInterp = flipAnim.interpolate({ inputRange: [0, 1], outputRange: ['-90deg', '0deg'] });

  if (loading) {
    return <SafeAreaView style={[s.container, s.center]}><ActivityIndicator color={COLORS.ink} /></SafeAreaView>;
  }

  if (cards.length === 0) {
    return (
      <SafeAreaView style={[s.container, s.center]}>
        <Text style={s.doneIcon}>🎉</Text>
        <Text style={s.doneTitle}>All caught up!</Text>
        <Text style={s.doneSub}>No cards due right now. Check back later.</Text>
      </SafeAreaView>
    );
  }

  if (done) {
    return (
      <SafeAreaView style={[s.container, s.center]}>
        <Text style={s.doneIcon}>✅</Text>
        <Text style={s.doneTitle}>Session complete!</Text>
        <Text style={s.doneSub}>You reviewed {cards.length} cards.</Text>
        <TouchableOpacity style={s.restartBtn} onPress={() => { setDone(false); setIdx(0); loadCards(); }}>
          <Text style={s.restartLabel}>Study More</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  const card = cards[idx];

  return (
    <SafeAreaView style={s.container}>
      <View style={s.topBar}>
        <Text style={s.counter}>{idx + 1} / {cards.length}</Text>
        {offlineMode && <Text style={s.offlineBadge}>📵 Offline</Text>}
      </View>

      {/* Progress bar */}
      <View style={s.progressBg}>
        <View style={[s.progressFill, { width: `${((idx) / cards.length) * 100}%` as any }]} />
      </View>

      {/* Card */}
      <ScrollView contentContainerStyle={s.cardArea}>
        {/* Front */}
        <Animated.View style={[s.card, { transform: [{ rotateY: frontInterp }] }, !flipped && s.cardVisible]}>
          <Text style={s.cardLabel}>QUESTION</Text>
          <Text style={s.cardText}>{card.front}</Text>
          <TouchableOpacity style={s.flipBtn} onPress={flipCard}>
            <Text style={s.flipBtnText}>Reveal Answer</Text>
          </TouchableOpacity>
        </Animated.View>

        {/* Back */}
        {flipped && (
          <Animated.View style={[s.card, s.cardBack, { transform: [{ rotateY: backInterp }] }]}>
            <Text style={s.cardLabel}>ANSWER</Text>
            <Text style={s.cardText}>{card.back}</Text>
          </Animated.View>
        )}
      </ScrollView>

      {/* Quality buttons */}
      {flipped && (
        <View style={s.qualityRow}>
          {QUALITY_LABELS.map(({ q, label, color, emoji }) => (
            <TouchableOpacity
              key={q}
              style={[s.qualBtn, { backgroundColor: color + '22', borderColor: color }]}
              onPress={() => handleQuality(q)}
            >
              <Text style={s.qualEmoji}>{emoji}</Text>
              <Text style={[s.qualLabel, { color }]}>{label}</Text>
            </TouchableOpacity>
          ))}
        </View>
      )}
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  center: { justifyContent: 'center', alignItems: 'center', padding: 32 },
  topBar: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 20, paddingTop: 8, paddingBottom: 4 },
  counter: { fontSize: 14, fontWeight: '700', color: COLORS.ink2 },
  offlineBadge: { fontSize: 12, color: COLORS.amber, fontWeight: '600' },
  progressBg: { height: 4, backgroundColor: COLORS.border, marginHorizontal: 20, borderRadius: 2 },
  progressFill: { height: 4, backgroundColor: COLORS.blue, borderRadius: 2 },
  cardArea: { padding: 20, paddingBottom: 8, alignItems: 'center' },
  card: { width: '100%', backgroundColor: COLORS.surface, borderRadius: 20, padding: 28, minHeight: 200, shadowColor: '#000', shadowOpacity: 0.08, shadowRadius: 16, elevation: 4, alignItems: 'center' },
  cardBack: { borderTopColor: COLORS.green, borderTopWidth: 3 },
  cardVisible: {},
  cardLabel: { fontSize: 10, fontWeight: '800', letterSpacing: 1.5, color: COLORS.ink2, marginBottom: 16 },
  cardText: { fontSize: 18, fontWeight: '600', color: COLORS.ink, textAlign: 'center', lineHeight: 26 },
  flipBtn: { marginTop: 24, backgroundColor: COLORS.ink, paddingHorizontal: 32, paddingVertical: 12, borderRadius: 100 },
  flipBtnText: { color: '#FFF', fontWeight: '700', fontSize: 14 },
  qualityRow: { flexDirection: 'row', paddingHorizontal: 12, paddingBottom: 16, gap: 6 },
  qualBtn: { flex: 1, borderWidth: 1.5, borderRadius: 10, paddingVertical: 8, alignItems: 'center' },
  qualEmoji: { fontSize: 18 },
  qualLabel: { fontSize: 10, fontWeight: '700', marginTop: 2 },
  doneIcon: { fontSize: 60, marginBottom: 12 },
  doneTitle: { fontSize: 24, fontWeight: '800', color: COLORS.ink, marginBottom: 8 },
  doneSub: { fontSize: 14, color: COLORS.ink2, textAlign: 'center' },
  restartBtn: { marginTop: 24, backgroundColor: COLORS.ink, paddingHorizontal: 40, paddingVertical: 14, borderRadius: 100 },
  restartLabel: { color: '#FFF', fontWeight: '700', fontSize: 15 },
});
