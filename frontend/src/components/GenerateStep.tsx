import { ApiKeyNotice } from "./ApiKeyNotice";
import { ImportPanel } from "./ImportPanel";
import { ProviderConfig } from "./ProviderConfig";
import { ThreatModelUpload } from "./ThreatModelUpload";
import { TopEventInput } from "./TopEventInput";
import type { FaultTree, Provider } from "../types";

interface GenerateStepProps {
  threatModelMarkdown: string;
  onThreatModelChange: (v: string) => void;
  topEvent: string;
  onTopEventChange: (v: string) => void;
  provider: Provider;
  onProviderChange: (p: Provider) => void;
  model: string;
  onModelChange: (m: string) => void;
  apiKey: string;
  onApiKeyChange: (k: string) => void;
  isGenerating: boolean;
  errorMessage: string | null;
  onGenerate: () => void;
  onImport: (tree: FaultTree) => void;
}

export function GenerateStep(props: GenerateStepProps) {
  const canGenerate =
    props.threatModelMarkdown.trim().length > 0 &&
    props.topEvent.trim().length > 0 &&
    props.apiKey.trim().length > 0;

  return (
    <div className="generate-step">
      <h1>fault-tree-ai</h1>
      <p className="intro">
        Draft a fault tree from a threat model, system document, or Mermaid diagram and a Top Event,
        then edit it, add controls, and quantify the risk.
      </p>

      <ThreatModelUpload value={props.threatModelMarkdown} onChange={props.onThreatModelChange} />
      <TopEventInput value={props.topEvent} onChange={props.onTopEventChange} />
      <ProviderConfig
        provider={props.provider}
        model={props.model}
        apiKey={props.apiKey}
        onProviderChange={props.onProviderChange}
        onModelChange={props.onModelChange}
        onApiKeyChange={props.onApiKeyChange}
      />
      <ApiKeyNotice />

      {props.errorMessage && <p className="error-text">{props.errorMessage}</p>}

      <button type="button" disabled={!canGenerate || props.isGenerating} onClick={props.onGenerate}>
        {props.isGenerating ? "Generating…" : "Generate fault tree"}
      </button>

      <hr />

      <p className="muted">Already have an FTA JSON export from a previous session? Skip generation:</p>
      <ImportPanel hasExistingAnalysis={false} onCreateFromImport={props.onImport} />
    </div>
  );
}
