import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-bg-primary grid-bg text-center p-8">
      <div className="text-8xl font-bold text-accent-cyan/20 font-mono mb-2">404</div>
      <h1 className="text-xl font-bold text-accent-cyan mb-2">PAGE NOT FOUND</h1>
      <p className="text-sm text-text-secondary mb-8 max-w-sm">
        The route you requested does not exist in the TPT Observer.
      </p>
      <Link
        href="/"
        className="px-6 py-2.5 rounded bg-accent-cyan/20 text-accent-cyan text-sm border border-accent-cyan/50 hover:bg-accent-cyan/30 transition-colors"
      >
        Return to Dashboard
      </Link>
    </div>
  );
}
