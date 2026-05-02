/**
 * Dashboard screen — XP, level, streak, quick actions, today's activity
 */
import { useEffect, useState } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  ActivityIndicator, RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { useAuthStore } from '@/store/authStore';
import { progressApi } from '@/lib/api';
import { syncModules } from '@/lib/database';

interface DayHistory { date: string; xp_gained: number; lessons: number; cards: number; }
interface Stats { xp: number; level: number; streak_days: number; lessons_completed: number; cards_reviewed: number; }

const COLORS = { bg: '#F5F0E8', ink: '#1A1A1A', ink2: '#6B6B6B', surface: '#FFFFFF', border: '#E8E3D9', green: '#22C55E', amber: '#F59E0B', blue: '#3B82F6' };

export default function DashboardScreen() {
  const { user, loadUser } = useAuthStore();
  const [stats, setStats] = useState<Stats | null>(null);
  const [history, setHistory] = useState<DayHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    try {
      const [statsRes, histRes] = await Promise.all([
        progressApi.getStats(),
        progressApi.getHistory(14),
      ]);
      setStats(statsRes.data);
      setHistory(histRes.data);
    } catch {}
    finally { setLoading(false); setRefreshing(false); }
  };

  useEffect(() => {
    load();
    syncModules().catch(() => {});
  }, []);

  const onRefresh = () => { setRefreshing(true); loadUser(); load(); };

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
          <View>
            <Text style={s.greeting}>Good {greeting()}, {user?.first_name ?? 'Doctor'} 👋</Text>
            <Text style={s.subGreeting}>Keep up the great work!</Text>
          </View>
        </View>

        {/* XP / Level / Streak row */}
        <View style={s.statsRow}>
          <StatCard label="Level" value={String(user?.level ?? 1)} color={COLORS.amber} />
          <StatCard label="XP" value={fmtNum(user?.xp ?? 0)} color={COLORS.blue} />
          <StatCard label="Streak" value={`${user?.streak_days ?? 0}🔥`} color={COLORS.green} />
        </View>

        {/* Progress compact */}
        {stats && (
          <View style={s.progressCard}>
            <Text style={s.cardTitle}>This Month</Text>
            <View style={s.progressRow}>
              <View style={s.progressItem}>
                <Text style={s.progressVal}>{stats.lessons_completed}</Text>
                <Text style={s.progressLabel}>Lessons</Text>
              </View>
              <View style={s.divider} />
              <View style={s.progressItem}>
                <Text style={s.progressVal}>{stats.cards_reviewed}</Text>
                <Text style={s.progressLabel}>Cards</Text>
              </View>
            </View>
          </View>
        )}

        {/* Activity chart (14 days) */}
        {history.length > 0 && (
          <View style={s.chartCard}>
            <Text style={s.cardTitle}>Activity (14 days)</Text>
            <View style={s.chart}>
              {history.map((d) => (
                <View key={d.date} style={s.barWrapper}>
                  <View
                    style={[
                      s.bar,
                      { height: Math.max(4, (d.cards / maxCards) * 60) },
                    ]}
                  />
                  <Text style={s.barLabel}>{d.date.slice(8)}</Text>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* Quick actions */}
        <Text style={s.sectionTitle}>Quick Actions</Text>
        <View style={s.actionsGrid}>
          <ActionCard icon="⚡" label="Review Cards" color="#EFF6FF" onPress={() => router.push('/(tabs)/flashcards')} />
          <ActionCard icon="🤖" label="Ask AI" color="#F0FFF4" onPress={() => router.push('/(tabs)/ai')} />
          <ActionCard icon="📚" label="Browse Library" color="#FFFBEB" onPress={() => router.push('/(tabs)/modules')} />
          <ActionCard icon="📊" label="Progress" color="#FFF5F5" onPress={() => {}} />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

function StatCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <View style={[s.statCard, { borderTopColor: color, borderTopWidth: 3 }]}>
      <Text style={s.statVal}>{value}</Text>
      <Text style={s.statLabel}>{label}</Text>
    </View>
  );
}

function ActionCard({ icon, label, color, onPress }: { icon: string; label: string; color: string; onPress: () => void }) {
  return (
    <TouchableOpacity style={[s.actionCard, { backgroundColor: color }]} onPress={onPress} activeOpacity={0.75}>
      <Text style={s.actionIcon}>{icon}</Text>
      <Text style={s.actionLabel}>{label}</Text>
    </TouchableOpacity>
  );
}

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return 'morning';
  if (h < 17) return 'afternoon';
  return 'evening';
}

function fmtNum(n: number) {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  center: { justifyContent: 'center', alignItems: 'center' },
  scroll: { padding: 20, paddingBottom: 40 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  greeting: { fontSize: 22, fontWeight: '700', color: COLORS.ink },
  subGreeting: { fontSize: 13, color: COLORS.ink2, marginTop: 2 },
  statsRow: { flexDirection: 'row', gap: 10, marginBottom: 16 },
  statCard: { flex: 1, backgroundColor: COLORS.surface, borderRadius: 12, padding: 14, alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 8, elevation: 2 },
  statVal: { fontSize: 20, fontWeight: '800', color: COLORS.ink },
  statLabel: { fontSize: 11, color: COLORS.ink2, marginTop: 2, fontWeight: '600' },
  progressCard: { backgroundColor: COLORS.surface, borderRadius: 12, padding: 16, marginBottom: 16, shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 8, elevation: 2 },
  cardTitle: { fontSize: 13, fontWeight: '700', color: COLORS.ink, marginBottom: 12 },
  progressRow: { flexDirection: 'row', justifyContent: 'space-around' },
  progressItem: { alignItems: 'center' },
  progressVal: { fontSize: 24, fontWeight: '800', color: COLORS.ink },
  progressLabel: { fontSize: 12, color: COLORS.ink2, marginTop: 2 },
  divider: { width: 1, backgroundColor: COLORS.border },
  chartCard: { backgroundColor: COLORS.surface, borderRadius: 12, padding: 16, marginBottom: 16, shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 8, elevation: 2 },
  chart: { flexDirection: 'row', alignItems: 'flex-end', gap: 4, height: 72 },
  barWrapper: { flex: 1, alignItems: 'center' },
  bar: { width: '80%', backgroundColor: COLORS.blue, borderRadius: 3, minHeight: 4 },
  barLabel: { fontSize: 9, color: COLORS.ink2, marginTop: 3 },
  sectionTitle: { fontSize: 15, fontWeight: '700', color: COLORS.ink, marginBottom: 12 },
  actionsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  actionCard: { width: '47%', borderRadius: 12, padding: 16, gap: 8 },
  actionIcon: { fontSize: 28 },
  actionLabel: { fontSize: 13, fontWeight: '700', color: COLORS.ink },
});
