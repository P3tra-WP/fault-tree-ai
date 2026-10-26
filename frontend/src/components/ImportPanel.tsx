import { useState, type ChangeEvent } from "react";
import type { FaultTree } from "../types";

interface ImportPanelProps {
  hasExistingAnalysis: boolean;
  onCreateFromImport?: (tree: FaultTree) => void;
  onReplace?: (tree: FaultTree) => void;
  onStartMerge?: (tree: FaultTree) => void;
}

function extractFaultTree(parsed: unknown): FaultTree {
  if (parsed && typeof parsed === "object" && "fault_tree" in parsed) {
    return (parsed as { fault_tree: FaultTree }).fault_tree;
  }
  return parsed as FaultTree;
}

export function ImportPanel({ hasExistingAnalysis, onCreateFromImport, onReplace, onStartMerge }: ImportPanelProps) {
  const [pending, setPending] = useState<FaultTree | null>(null);
  const [error, setError] = useState<string | null>(null);

  function handleFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(String(reader.result ?? ""));
        const tree = extractFaultTree(parsed);
        setError(null);
        if (hasExistingAnalysis) {
          setPending(tree);
        } else {
          onCreateFromImport?.(tree);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Invalid JSON file");
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  }

  return (
    <div className="field import-panel">
      <label>Import a previous FTA JSON export</label>
      <input type="file" accept=".json,application/json" onChange={handleFile} />
      {error && <p className="error-text">{error}</p>}
      {pending && (
        <div className="import-mode-choice">
          <p>Replace the current tree, or merge this one in as a new subtree?</p>
          <button
            type="button"
            onClick={() => {
              onReplace?.(pending);
              setPending(null);
            }}
          >
            Replace current tree
          </button>
          <button
            type="button"
            onClick={() => {
              onStartMerge?.(pending);
              setPending(null);
            }}
          >
            Merge as subtree…
          </button>
          <button type="button" onClick={() => setPending(null)}>
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
