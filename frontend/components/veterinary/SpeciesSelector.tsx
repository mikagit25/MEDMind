"use client";

const SPECIES = [
  { id: "dog",     name: "Dog",         icon: "🐕", category: "small_animal" },
  { id: "cat",     name: "Cat",         icon: "🐈", category: "small_animal" },
  { id: "rabbit",  name: "Rabbit",      icon: "🐇", category: "small_animal" },
  { id: "horse",   name: "Horse",       icon: "🐎", category: "large_animal" },
  { id: "cattle",  name: "Cattle",      icon: "🐄", category: "large_animal" },
  { id: "sheep",   name: "Sheep",       icon: "🐑", category: "large_animal" },
  { id: "pig",     name: "Pig",         icon: "🐷", category: "large_animal" },
  { id: "bird",    name: "Bird/Avian",  icon: "🦜", category: "exotic" },
  { id: "reptile", name: "Reptile",     icon: "🦎", category: "exotic" },
];

interface Props {
  value: string | null;
  onChange: (speciesId: string) => void;
}

export function SpeciesSelector({ value, onChange }: Props) {
  const categories = [
    { id: "small_animal", label: "Small Animals" },
    { id: "large_animal", label: "Large Animals" },
    { id: "exotic",       label: "Exotic" },
  ];

  return (
    <div className="space-y-3">
      {categories.map(cat => (
        <div key={cat.id}>
          <div className="text-xs font-semibold text-ink-3 uppercase tracking-wide mb-2">{cat.label}</div>
          <div className="flex flex-wrap gap-2">
            {SPECIES.filter(s => s.category === cat.id).map(s => (
              <button
                key={s.id}
                onClick={() => onChange(s.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm border transition-colors ${
                  value === s.id
                    ? "bg-accent text-white border-accent"
                    : "border-border text-ink hover:border-accent"
                }`}
              >
                <span>{s.icon}</span>
                <span>{s.name}</span>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
