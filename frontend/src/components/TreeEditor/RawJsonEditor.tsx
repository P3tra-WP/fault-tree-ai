import { useState } from "react";
import type { FaultTree } from "../../types";

interface RawJsonEditorProps {
  faultTree: FaultTree;
  onApply: (tree: FaultTree) => void;
}

export function RawJsonEditor({ faultTree, onApply }: RawJsonEditorProps) {
  const [text, setText] = useState(() => JSON.stringify(faultTree, null, 2));
  const [error, setError] = useState<string | null>(null);

  function apply() {
    try {
      const parsed = JSON.parse(text) as FaultTree;
      setError(null);
      onApply(parsed);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invalid JSON");
    }
  }

  function reset() {
    setText(JSON.stringify(faultTree, null, 2));
    setError(null);
  }

  return (
    <div className="raw-json-editor">
      <textarea value={text} onChange={(e) => setText(e.target.value)} spellCheck={false} rows={20} />
      {error && <p className="error-text">{error}</p>}
      <div className="raw-json-actions">
        <button type="button" onClick={apply}>
          Apply JSON
        </button>
        <button type="button" onClick={reset}>
          Reset to current tree
        </button>
      </div>
    </div>
  );
}
