export default function OfflinePage() {
  return (
    <main className="min-h-screen flex items-center justify-center p-6 bg-bg">
      <div className="text-center max-w-sm">
        <div className="text-6xl mb-6">📡</div>
        <h1 className="font-syne font-black text-2xl text-ink mb-3">You're offline</h1>
        <p className="font-serif text-ink-3 text-sm mb-6">
          No internet connection. Pages you've previously visited may still be available.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="btn-primary"
        >
          Try again
        </button>
      </div>
    </main>
  );
}
