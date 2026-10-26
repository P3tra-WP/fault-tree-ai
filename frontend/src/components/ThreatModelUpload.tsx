import type { ChangeEvent } from "react";

interface ThreatModelUploadProps {
  value: string;
  onChange: (markdown: string) => void;
}

export function ThreatModelUpload({ value, onChange }: ThreatModelUploadProps) {
  function handleFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => onChange(String(reader.result ?? ""));
    reader.readAsText(file);
  }

  return (
    <div className="field">
      <label>Threat model or system document</label>
      <input
        type="file"
        accept=".md,.txt,.json,.mmd,.mermaid,text/markdown,text/plain,application/json"
        onChange={handleFile}
      />
      <textarea
        placeholder="Paste or upload Markdown, JSON, or Mermaid source (assets, trust boundaries, attacker goals)..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={10}
      />
    </div>
  );
}
