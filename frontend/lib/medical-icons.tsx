import {
  Heart, HeartPulse, Brain, Stethoscope, Pill, Syringe,
  FlaskConical, Baby, PawPrint, Eye, Ear, Droplet, Droplets,
  Wind, Bone, Bug, BookOpen, Microscope, Ambulance, Apple,
  Scissors, Activity, Ribbon, RefreshCw, Users, Scan, Hand,
  FileText, Zap, Search, RotateCcw,
  type LucideProps,
} from "lucide-react";

export type IconProps = LucideProps;

// ── Category → Icon mapping ───────────────────────────────────────────────────
const ICON_MAP: Record<string, React.ComponentType<LucideProps>> = {
  diseases:             HeartPulse,
  drugs:                Pill,
  procedures:           Syringe,
  symptoms:             Stethoscope,
  diagnostics:          Microscope,
  emergency:            Ambulance,
  nutrition:            Apple,
  pediatrics:           Baby,
  cardiology:           Heart,
  neurology:            Brain,
  oncology:             Ribbon,
  surgery:              Scissors,
  psychiatry:           Brain,
  endocrinology:        Activity,
  "infectious-diseases": Bug,
  veterinary:           PawPrint,
  pharmacology:         Pill,
  "internal-medicine":  Stethoscope,
  "ob-gyn":             Baby,
  orthopedics:          Bone,
  rheumatology:         Hand,
  hematology:           Droplet,
  nephrology:           Droplets,
  pulmonology:          Wind,
  ophthalmology:        Eye,
  ent:                  Ear,
  urology:              FlaskConical,
  geriatrics:           Users,
  dermatology:          Scan,
};

const DEFAULT_ICON = FileText;

export function CategoryIcon({
  category,
  size = 18,
  className,
  strokeWidth = 1.75,
}: {
  category: string;
  size?: number;
  className?: string;
  strokeWidth?: number;
}) {
  const Icon = ICON_MAP[category] ?? DEFAULT_ICON;
  return <Icon size={size} className={className} strokeWidth={strokeWidth} />;
}

// ── Feature icons (Landing page) ──────────────────────────────────────────────
export const FEATURE_ICONS: Record<string, React.ComponentType<LucideProps>> = {
  tutor:      Brain,
  flashcards: RotateCcw,
  cases:      Stethoscope,
  modules:    BookOpen,
  pubmed:     Microscope,
  veterinary: PawPrint,
};

export function FeatureIcon({
  name,
  size = 22,
  className,
  strokeWidth = 1.75,
}: {
  name: string;
  size?: number;
  className?: string;
  strokeWidth?: number;
}) {
  const Icon = FEATURE_ICONS[name] ?? Zap;
  return <Icon size={size} className={className} strokeWidth={strokeWidth} />;
}

// ── Specialty icons (Landing page) ────────────────────────────────────────────
export const SPECIALTY_ICONS: Record<string, React.ComponentType<LucideProps>> = {
  Cardiology:   Heart,
  Neurology:    Brain,
  Surgery:      Scissors,
  Pediatrics:   Baby,
  "OB/GYN":     Baby,
  Therapy:      Stethoscope,
  // Russian
  Кардиология:  Heart,
  Неврология:   Brain,
  Хирургия:     Scissors,
  Педиатрия:    Baby,
  "Акушерство / Гинекология": Baby,
  Терапия:      Stethoscope,
};

export function SpecialtyIcon({
  name,
  size = 28,
  className,
  strokeWidth = 1.5,
}: {
  name: string;
  size?: number;
  className?: string;
  strokeWidth?: number;
}) {
  const Icon = SPECIALTY_ICONS[name] ?? Activity;
  return <Icon size={size} className={className} strokeWidth={strokeWidth} />;
}
