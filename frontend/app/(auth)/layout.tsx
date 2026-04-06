export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Brand */}
        <div className="text-center mb-8">
          <div className="font-syne font-black text-4xl text-ink tracking-tight">
            Med<span className="text-red">Mind</span>
          </div>
          <div className="text-ink-3 font-serif text-sm mt-1">Medical Education Platform</div>
        </div>
        {children}
      </div>
    </div>
  );
}
