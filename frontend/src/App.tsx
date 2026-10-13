import RunForm from "./components/RunForm";

export default function App() {
  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-2xl space-y-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-semibold">tradeagents</h1>
          <p className="text-sm text-slate-400">
            Multi-agent analysis: analysts produce reports, a research debate
            forms a plan, a trader commits, and a risk debate decides the rating.
          </p>
        </header>
        <RunForm />
      </div>
    </div>
  );
}