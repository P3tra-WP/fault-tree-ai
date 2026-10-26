import mermaid from "mermaid";
import { useEffect, useRef, useState } from "react";

import { faultTreeToMermaid } from "../lib/mermaid";
import type { FaultTree } from "../types";

mermaid.initialize({ startOnLoad: false, theme: "neutral" });

let renderCounter = 0;

interface FaultTreeDiagramProps {
  faultTree: FaultTree;
}

export function FaultTreeDiagram({ faultTree }: FaultTreeDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const definition = faultTreeToMermaid(faultTree);
    renderCounter += 1;
    const id = `fault-tree-diagram-${renderCounter}`;

    mermaid
      .render(id, definition)
      .then(({ svg }) => {
        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg;
          setError(null);
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to render diagram");
      });

    return () => {
      cancelled = true;
    };
  }, [faultTree]);

  return (
    <div className="fault-tree-diagram">
      {error && <p className="error-text">{error}</p>}
      <div ref={containerRef} />
    </div>
  );
}
