/**
 * Modules library screen — browse specialties and modules
 */
import { useEffect, useState } from 'react';
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  ActivityIndicator, TextInput, RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { contentApi } from '@/lib/api';

interface Module { id: string; title: string; description: string; is_fundamental: boolean; lesson_count: number; flashcard_count: number; }
interface Specialty { id: string; name: string; icon: string; modules: Module[]; }

const COLORS = { bg: '#F5F0E8', ink: '#1A1A1A', ink2: '#6B6B6B', surface: '#FFFFFF', border: '#E8E3D9', blue: '#3B82F6', amber: '#F59E0B' };

export default function ModulesScreen() {
  const [specialties, setSpecialties] = useState<Specialty[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState('');
  const [expanded, setExpanded] = useState<string | null>(null);

  const load = async () => {
    try {
      const res = await contentApi.getSpecialties();
      const specs: Specialty[] = [];
      for (const spec of res.data) {
        try {
          const mods = await contentApi.getModules(spec.id);
          specs.push({ ...spec, modules: mods.data });
        } catch {
          specs.push({ ...spec, modules: [] });
        }
      }
      setSpecialties(specs);
    } catch {}
    finally { setLoading(false); setRefreshing(false); }
  };

  useEffect(() => { load(); }, []);

  const filtered = specialties.map((spec) => ({
    ...spec,
    modules: spec.modules.filter(
      (m) =>
        !search ||
        m.title.toLowerCase().includes(search.toLowerCase()) ||
        m.description?.toLowerCase().includes(search.toLowerCase())
    ),
  })).filter((spec) => !search || spec.modules.length > 0);

  if (loading) {
    return <SafeAreaView style={[s.container, s.center]}><ActivityIndicator color={COLORS.ink} /></SafeAreaView>;
  }

  return (
    <SafeAreaView style={s.container}>
      <View style={s.header}>
        <Text style={s.headerTitle}>📚 Library</Text>
        <TextInput
          style={s.searchInput}
          value={search}
          onChangeText={setSearch}
          placeholder="Search modules…"
          placeholderTextColor={COLORS.ink2}
          clearButtonMode="while-editing"
        />
      </View>

      <FlatList
        data={filtered}
        keyExtractor={(item) => item.id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} />}
        contentContainerStyle={s.list}
        renderItem={({ item: spec }) => (
          <View style={s.specSection}>
            <TouchableOpacity
              style={s.specHeader}
              onPress={() => setExpanded((e) => (e === spec.id ? null : spec.id))}
              activeOpacity={0.75}
            >
              <Text style={s.specIcon}>{spec.icon ?? '📖'}</Text>
              <View style={s.specInfo}>
                <Text style={s.specName}>{spec.name}</Text>
                <Text style={s.specCount}>{spec.modules.length} modules</Text>
              </View>
              <Text style={s.chevron}>{expanded === spec.id ? '▲' : '▼'}</Text>
            </TouchableOpacity>

            {(expanded === spec.id || !!search) && spec.modules.map((mod) => (
              <View key={mod.id} style={s.modCard}>
                <View style={s.modRow}>
                  <View style={s.modInfo}>
                    <Text style={s.modTitle}>{mod.title}</Text>
                    {mod.description ? (
                      <Text style={s.modDesc} numberOfLines={2}>{mod.description}</Text>
                    ) : null}
                  </View>
                  {mod.is_fundamental && (
                    <View style={s.fundamentalBadge}>
                      <Text style={s.fundamentalText}>FREE</Text>
                    </View>
                  )}
                </View>
                <View style={s.modMeta}>
                  <Text style={s.metaChip}>📖 {mod.lesson_count ?? 0} lessons</Text>
                  <Text style={s.metaChip}>⚡ {mod.flashcard_count ?? 0} cards</Text>
                </View>
              </View>
            ))}
          </View>
        )}
      />
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  center: { justifyContent: 'center', alignItems: 'center' },
  header: { padding: 16, paddingBottom: 8 },
  headerTitle: { fontSize: 22, fontWeight: '800', color: COLORS.ink, marginBottom: 10 },
  searchInput: { backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 10, fontSize: 14, color: COLORS.ink },
  list: { padding: 16, gap: 12 },
  specSection: { backgroundColor: COLORS.surface, borderRadius: 14, overflow: 'hidden', shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 8, elevation: 2 },
  specHeader: { flexDirection: 'row', alignItems: 'center', padding: 14, gap: 10 },
  specIcon: { fontSize: 24 },
  specInfo: { flex: 1 },
  specName: { fontSize: 15, fontWeight: '700', color: COLORS.ink },
  specCount: { fontSize: 12, color: COLORS.ink2, marginTop: 1 },
  chevron: { fontSize: 12, color: COLORS.ink2 },
  modCard: { borderTopWidth: 1, borderTopColor: COLORS.border, padding: 14 },
  modRow: { flexDirection: 'row', gap: 10, marginBottom: 8 },
  modInfo: { flex: 1 },
  modTitle: { fontSize: 14, fontWeight: '600', color: COLORS.ink },
  modDesc: { fontSize: 12, color: COLORS.ink2, marginTop: 3, lineHeight: 17 },
  fundamentalBadge: { backgroundColor: '#F0FFF4', borderRadius: 6, paddingHorizontal: 6, paddingVertical: 2, alignSelf: 'flex-start' },
  fundamentalText: { fontSize: 10, fontWeight: '800', color: '#16A34A' },
  modMeta: { flexDirection: 'row', gap: 8 },
  metaChip: { fontSize: 11, color: COLORS.ink2, fontWeight: '500' },
});
