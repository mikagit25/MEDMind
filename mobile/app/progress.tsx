/**
 * Progress screen — stats, 14-day activity chart, weekly quiz accuracy
 */
import { useEffect, useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet,
  ActivityIndicator, TouchableOpacity, RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { progressApi } from '@/lib/api';

interface Stats {
  xp: number;
  level: number;
  streak_days: number;
  lessons_completed: number;
  cards_reviewed: number;
  mcqs_answered: number;
  correct_rate: number;
}

interface DayHistory {
  date: string;
  xp_gained: number;
  lessons: number;
  cards: number;
}

interface WeekTrend {
  week_start: string;
  accuracy_pct: number;
  total_questions: number;
  session_count: number;
}

const COLORS = {
  bg: '#F5F0E8',
  ink: '#1A1A1A',
  ink2: '#6B6B6B',
  ink3: '#A0A0A0',
  surface: '#FFFFFF',
  border: '#E8E3D9',
  green: '#22C55E',
  amber: '#F59E0B',
  blue: '#3B82F6',
  red: '#EF4444',
};

export default function ProgressScreen() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [history, setHistory] = useState<DayHistory[]>([]);
  const [weeklyTrend, setWeeklyTrend] = useState<WeekTrend[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    try {
      const [statsRes, histRes, trendRes] = await Promise.all([
        progressApi.getStats(),
        progressApi.getHistory(14),
        progressApi.getQuizWeeklyTrend().catch(() => null),
      ]);
      setStats(statsRes.data);
      setHistory(histRes.data ?? []);
      if (trendRes?.data?.weeks) setWeeklyTrend(trendRes.data.weeks);
    } catch {}
    finally { setLoading(false); setRefreshing(false); }
  };

  useEffect(() => { load(); }, []);

  const onRefresh = () => { setRefreshing(true); load(); };

  const maxCards = Math.max(...history.map((d) => d.cards), 1);

  if (loading) {
    return (
      <SafeAreaView style={[s.container, s.center]}>
        <ActivityIndicator color={COLORS.ink} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={s.container}>
      <ScrollView
        contentContainerStyle={s.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {/* Header */}
        <View style={s.header}>
          <TouchableOpacity onPress={() => router.back()} style={s.backBtn}>
            <Text style={s.backText}>← Back</Text>
          </TouchableOpacity>
          <Text style={s.title}>My Progress</Text>
        </View>

        {/* Key stats */}
        {stats && (
          <View style={s.statsGrid}>
            <StatBox label="Lessons" value={String(stats.lessons_completed)} color={COLORS.blue} />
            <StatBox label="Cards" value={String(stats.cards_reviewed)} color={COLORS.green} />
            <StatBox label="MCQs" value={String(stats.mcqs_answered)} color={COLORS.amber} />
            <StatBox
              label="Accuracy"
              value={stats.correct_rate > 0 ? `${Math.round(stats.correct_rate)}%` : '—'}
              color={stats.correct_rate >= 75 ? COLORS.green : stats.correct_rate >= 50 ? COLORS.amber : COLORS.red}
            />
          </View>
        )}

        {/* 14-day activity bar chart */}
        {history.length > 0 && (
          <View style={s.card}>
            <Text style={s.cardTitle}>Activity (14 days)</Text>
            <View style={s.chart}>
              {history.map((d) => (
                <View key={d.date} style={s.barWrapper}>
                  <View
                    style={[
                      s.bar,
                      { height: Math.max(4, (d.cards / maxCards) * 60), backgroundColor: COLORS.blue },
                    ]}
                  />
                  <Text style={s.barLabel}>{d.date.slice(8)}</Text>
                </View>
              ))}
            </View>
            <Text style={s.chartHint}>Cards reviewed per day</Text>
          </View>
        )}

        {/* Weekly quiz accuracy */}
        {weeklyTrend.length > 0 && (
          <View style={s.card}>
            <Text style={s.cardTitle}>Quiz Accuracy (8 weeks)</Text>
            {/* Week-over-week summary */}
            {weeklyTrend.length >= 2 && (() => {
              const latest = weeklyTrend[weeklyTrend.length - 1];
              const prev = weeklyTrend[weeklyTrend.length - 2];
              const delta = latest.accuracy_pct - prev.accuracy_pct;
              const deltaColor = delta >= 0 ? COLORS.green : COLORS.red;
              return (
                <View style={s.summaryRow}>
                  <View>
                    <Text style={s.summaryPct}>{latest.accuracy_pct.toFixed(0)}%</Text>
                    <Text style={s.summaryLabel}>This week · {latest.total_questions}Q</Text>
                  </View>
                  <Text style={[s.summaryDelta, { color: deltaColor }]}>
                    {delta >= 0 ? '▲' : '▼'} {Math.abs(delta).toFixed(0)}pp vs last week
                  </Text>
                </View>
              );
            })()}
            <View style={s.chart}>
              {weeklyTrend.map((w) => {
                const pct = w.accuracy_pct;
                const barH = Math.max(4, (pct / 100) * 60);
                const barColor = pct >= 75 ? COLORS.green : pct >= 50 ? COLORS.amber : COLORS.red;
                const label = w.week_start.slice(5, 10).replace('-', '/');
                return (
                  <View key={w.week_start} style={s.barWrapper}>
                    <View style={[s.bar, { height: barH, backgroundColor: barColor }]} />
                    <Text style={s.barLabel}>{label}</Text>
                  </View>
                );
              })}
            </View>
          </View>
        )}

        {/* Empty state */}
        {history.length === 0 && weeklyTrend.length === 0 && (
          <View style={s.empty}>
            <Text style={s.emptyIcon}>📊</Text>
            <Text style={s.emptyText}>No activity yet.</Text>
            <Text style={s.emptySubtext}>Complete lessons and review cards to see your progress here.</Text>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function StatBox({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <View style={[s.statBox, { borderTopColor: color, borderTopWidth: 3 }]}>
      <Text style={s.statVal}>{value}</Text>
      <Text style={s.statLabel}>{label}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  center: { justifyContent: 'center', alignItems: 'center' },
  scroll: { padding: 20, paddingBottom: 40 },
  header: { flexDirection: 'row', alignItems: 'center', marginBottom: 20, gap: 12 },
  backBtn: { paddingVertical: 4, paddingRight: 8 },
  backText: { fontSize: 14, color: COLORS.ink2, fontWeight: '600' },
  title: { fontSize: 20, fontWeight: '800', color: COLORS.ink },
  statsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 16 },
  statBox: {
    width: '47%',
    backgroundColor: COLORS.surface,
    borderRadius: 12,
    padding: 14,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.04,
    shadowRadius: 8,
    elevation: 2,
  },
  statVal: { fontSize: 22, fontWeight: '800', color: COLORS.ink },
  statLabel: { fontSize: 11, color: COLORS.ink2, marginTop: 2, fontWeight: '600' },
  card: {
    backgroundColor: COLORS.surface,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOpacity: 0.04,
    shadowRadius: 8,
    elevation: 2,
  },
  cardTitle: { fontSize: 13, fontWeight: '700', color: COLORS.ink, marginBottom: 12 },
  chart: { flexDirection: 'row', alignItems: 'flex-end', gap: 4, height: 72 },
  barWrapper: { flex: 1, alignItems: 'center' },
  bar: { width: '80%', borderRadius: 3, minHeight: 4 },
  barLabel: { fontSize: 9, color: COLORS.ink3, marginTop: 3 },
  chartHint: { fontSize: 10, color: COLORS.ink3, marginTop: 6 },
  summaryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  summaryPct: { fontSize: 26, fontWeight: '800', color: COLORS.ink },
  summaryLabel: { fontSize: 10, color: COLORS.ink3, marginTop: 1 },
  summaryDelta: { fontSize: 13, fontWeight: '700' },
  empty: { alignItems: 'center', paddingTop: 40, gap: 8 },
  emptyIcon: { fontSize: 40 },
  emptyText: { fontSize: 16, fontWeight: '700', color: COLORS.ink },
  emptySubtext: { fontSize: 13, color: COLORS.ink2, textAlign: 'center', maxWidth: 280 },
});
