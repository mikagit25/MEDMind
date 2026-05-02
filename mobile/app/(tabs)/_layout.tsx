import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

const ACTIVE = '#1A1A1A';
const INACTIVE = '#9B9B9B';
const BG = '#F5F0E8';

type IconName = React.ComponentProps<typeof Ionicons>['name'];

function icon(name: IconName, focused: boolean) {
  return <Ionicons name={focused ? name : `${name}-outline` as IconName} size={24} color={focused ? ACTIVE : INACTIVE} />;
}

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: { backgroundColor: BG, borderTopColor: '#E8E3D9' },
        tabBarActiveTintColor: ACTIVE,
        tabBarInactiveTintColor: INACTIVE,
        tabBarLabelStyle: { fontFamily: 'System', fontSize: 11, fontWeight: '600' },
      }}
    >
      <Tabs.Screen
        name="dashboard"
        options={{ title: 'Home', tabBarIcon: ({ focused }) => icon('home', focused) }}
      />
      <Tabs.Screen
        name="flashcards"
        options={{ title: 'Flashcards', tabBarIcon: ({ focused }) => icon('layers', focused) }}
      />
      <Tabs.Screen
        name="ai"
        options={{ title: 'AI Tutor', tabBarIcon: ({ focused }) => icon('sparkles', focused) }}
      />
      <Tabs.Screen
        name="modules"
        options={{ title: 'Library', tabBarIcon: ({ focused }) => icon('book', focused) }}
      />
      <Tabs.Screen
        name="leaderboard"
        options={{ title: 'Rankings', tabBarIcon: ({ focused }) => icon('trophy', focused) }}
      />
      <Tabs.Screen
        name="achievements"
        options={{ title: 'Badges', tabBarIcon: ({ focused }) => icon('medal', focused) }}
      />
    </Tabs>
  );
}
