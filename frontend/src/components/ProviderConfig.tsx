import type { Provider } from "../types";

const MODELS: Record<Provider, string[]> = {
  anthropic: ["claude-sonnet-5", "claude-opus-4-8"],
  openai: ["gpt-5"],
  gemini: ["gemini-3.8-flash", "gemini-3.1-pro-preview"],
};

interface ProviderConfigProps {
  provider: Provider;
  model: string;
  apiKey: string;
  onProviderChange: (p: Provider) => void;
  onModelChange: (m: string) => void;
  onApiKeyChange: (k: string) => void;
}

export function ProviderConfig({
  provider,
  model,
  apiKey,
  onProviderChange,
  onModelChange,
  onApiKeyChange,
}: ProviderConfigProps) {
  return (
    <div className="field provider-config">
      <label>LLM provider</label>
      <div className="provider-radio-group">
        {(["anthropic", "openai", "gemini"] as Provider[]).map((p) => (
          <label key={p} className="radio-label">
            <input type="radio" name="provider" checked={provider === p} onChange={() => onProviderChange(p)} />
            {p === "anthropic" ? "Anthropic (Claude)" : p === "gemini" ? "Google (Gemini)" : "OpenAI"}
          </label>
        ))}
      </div>

      <label>Model</label>
      <select value={model} onChange={(e) => onModelChange(e.target.value)}>
        {MODELS[provider].map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>

      <label>API key</label>
      <input
        type="password"
        placeholder={provider === "gemini" ? "AIza..." : "API key"}
        value={apiKey}
        onChange={(e) => onApiKeyChange(e.target.value)}
        autoComplete="off"
      />
    </div>
  );
}

export { MODELS };
