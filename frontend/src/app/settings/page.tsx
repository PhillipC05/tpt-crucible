"use client";

import { useEffect, useState } from "react";
import { z } from "zod";

const SettingsSchema = z.object({
  llmProvider: z.enum(["none", "anthropic", "openrouter", "ollama", "spark"]).default("none"),
  llmApiKey: z.string().default(""),
  llmEndpoint: z.string().url().or(z.literal("")).default(""),
  llmModel: z.string().default(""),
  carbonRegion: z.string().default("us-east"),
});

type Settings = z.infer<typeof SettingsSchema>;

interface SparkStatus {
  detected: boolean;
  socket_path: string;
  platform: string;
  install_url: string;
}

const STORAGE_KEY = "tpt_settings";
const OBSERVER_API = process.env.NEXT_PUBLIC_OBSERVER_URL ?? "http://localhost:8080";

function loadSettings(): Settings {
  if (typeof window === "undefined") return SettingsSchema.parse({});
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return SettingsSchema.parse({});
    return SettingsSchema.parse(JSON.parse(raw));
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    return SettingsSchema.parse({});
  }
}

function saveSettings(s: Settings) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>(SettingsSchema.parse({}));
  const [saved, setSaved] = useState(false);
  const [spark, setSpark] = useState<SparkStatus | null>(null);
  const [sparkLoading, setSparkLoading] = useState(true);

  useEffect(() => {
    const loaded = loadSettings();
    setSettings(loaded);

    // Probe Observer for Spark presence
    fetch(`${OBSERVER_API}/api/spark/status`)
      .then((r) => r.json())
      .then((data: SparkStatus) => {
        setSpark(data);
        // Auto-set Spark as default when detected and no provider has been chosen yet
        if (data.detected && loaded.llmProvider === "none") {
          setSettings((s) => ({ ...s, llmProvider: "spark" }));
        }
      })
      .catch(() => setSpark(null))
      .finally(() => setSparkLoading(false));
  }, []);

  function update<K extends keyof Settings>(key: K, value: Settings[K]) {
    setSettings((s) => ({ ...s, [key]: value }));
    setSaved(false);
  }

  function handleSave() {
    const result = SettingsSchema.safeParse(settings);
    if (!result.success) return;
    saveSettings(result.data);
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  }

  const sparkDetected = spark?.detected === true;

  return (
    <div className="min-h-screen bg-bg-primary grid-bg p-6">
      <div className="max-w-2xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-accent-cyan">Settings</h1>
          <p className="text-sm text-text-secondary mt-1">Configure LLM provider, carbon region, and other preferences</p>
        </div>

        {/* Spark status banner */}
        {!sparkLoading && (
          <div className={`stat-card border ${sparkDetected ? "border-accent-cyan/40" : "border-border"}`}>
            <div className="flex items-start gap-3">
              <span className={`mt-0.5 text-lg ${sparkDetected ? "text-accent-cyan" : "text-text-secondary"}`}>
                {sparkDetected ? "⬡" : "○"}
              </span>
              <div className="flex-1 min-w-0">
                {sparkDetected ? (
                  <>
                    <p className="text-sm font-bold text-accent-cyan">TPT Spark detected</p>
                    <p className="text-xs text-text-secondary mt-0.5">
                      Running at <span className="font-mono text-text-primary">{spark?.socket_path}</span>.
                      Spark is set as your default LLM backend — fully offline, no API key required.
                    </p>
                  </>
                ) : (
                  <>
                    <p className="text-sm font-bold text-text-primary">TPT Spark not running</p>
                    <p className="text-xs text-text-secondary mt-0.5">
                      Install TPT Spark for offline, privacy-preserving AI assistance — no API key needed.{" "}
                      <a
                        href={spark?.install_url ?? "https://github.com/PhillipC05/tpt-spark"}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-accent-cyan underline hover:text-accent-cyan/80"
                      >
                        Get TPT Spark →
                      </a>
                    </p>
                  </>
                )}
              </div>
            </div>
          </div>
        )}

        <div className="stat-card space-y-4">
          <h3 className="text-sm font-bold text-accent-amber">LLM PROVIDER</h3>
          <p className="text-xs text-text-secondary">
            Used for AI-assisted features: driver generation, RTL assistance, error diagnosis, and NL hardware config.
            Leave as "None" to disable all AI features.
          </p>
          <p className="text-xs text-text-secondary">
            Priority order: <span className="font-mono text-text-primary">TPT Spark → Ollama → OpenRouter → Anthropic API</span>
          </p>

          <div>
            <label className="text-xs text-text-secondary block mb-1">Provider</label>
            <select
              value={settings.llmProvider}
              onChange={(e) => update("llmProvider", e.target.value as Settings["llmProvider"])}
              className="w-full bg-bg-tertiary border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-cyan"
            >
              <option value="none">None (disable AI features)</option>
              <option value="spark">
                TPT Spark (local GGUF via IPC){sparkDetected ? " — detected ✓" : ""}
              </option>
              <option value="ollama">Ollama (local)</option>
              <option value="openrouter">OpenRouter</option>
              <option value="anthropic">Anthropic API</option>
            </select>
          </div>

          {settings.llmProvider !== "none" && settings.llmProvider !== "spark" && (
            <div>
              <label className="text-xs text-text-secondary block mb-1">API Key</label>
              <input
                type="password"
                value={settings.llmApiKey}
                onChange={(e) => update("llmApiKey", e.target.value)}
                placeholder="sk-..."
                className="w-full bg-bg-tertiary border border-border rounded px-3 py-2 text-sm text-text-primary font-mono focus:outline-none focus:border-accent-cyan"
              />
            </div>
          )}

          {(settings.llmProvider === "ollama" || settings.llmProvider === "openrouter") && (
            <div>
              <label className="text-xs text-text-secondary block mb-1">Endpoint URL</label>
              <input
                type="url"
                value={settings.llmEndpoint}
                onChange={(e) => update("llmEndpoint", e.target.value)}
                placeholder="http://localhost:11434"
                className="w-full bg-bg-tertiary border border-border rounded px-3 py-2 text-sm text-text-primary font-mono focus:outline-none focus:border-accent-cyan"
              />
            </div>
          )}

          {settings.llmProvider !== "none" && (
            <div>
              <label className="text-xs text-text-secondary block mb-1">Model</label>
              <input
                type="text"
                value={settings.llmModel}
                onChange={(e) => update("llmModel", e.target.value)}
                placeholder={settings.llmProvider === "spark" ? "(uses loaded model in Spark)" : "claude-sonnet-4-6"}
                className="w-full bg-bg-tertiary border border-border rounded px-3 py-2 text-sm text-text-primary font-mono focus:outline-none focus:border-accent-cyan"
              />
            </div>
          )}
        </div>

        <div className="stat-card space-y-4">
          <h3 className="text-sm font-bold text-accent-amber">CARBON ESTIMATION</h3>
          <div>
            <label className="text-xs text-text-secondary block mb-1">Grid Carbon Region</label>
            <select
              value={settings.carbonRegion}
              onChange={(e) => update("carbonRegion", e.target.value)}
              className="w-full bg-bg-tertiary border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-cyan"
            >
              <option value="us-east">US East</option>
              <option value="us-west">US West</option>
              <option value="eu-fr">EU (France)</option>
              <option value="eu-de">EU (Germany)</option>
              <option value="eu-no">EU (Norway — hydro)</option>
              <option value="ap-au">Asia-Pacific (Australia)</option>
              <option value="ap-cn">Asia-Pacific (China)</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            className="px-6 py-2.5 rounded bg-accent-cyan/20 text-accent-cyan text-sm border border-accent-cyan/50 hover:bg-accent-cyan/30 transition-colors"
          >
            Save Settings
          </button>
          {saved && <span className="text-xs text-accent-green">Settings saved</span>}
        </div>
      </div>
    </div>
  );
}
