import { useState } from "react";
import { ControlForm } from "./ControlForm";
import type { BasicEvent, Control, FaultTreeNode, Gate } from "../types";

function collectBasicEvents(node: FaultTreeNode): BasicEvent[] {
  if (node.node_type === "BASIC") return [node];
  return node.children.flatMap(collectBasicEvents);
}

interface ControlsPanelProps {
  root: Gate;
  controls: Control[];
  onChange: (controls: Control[]) => void;
}

export function ControlsPanel({ root, controls, onChange }: ControlsPanelProps) {
  const basicEvents = collectBasicEvents(root);
  const [showForm, setShowForm] = useState(false);

  function addControl(control: Control) {
    onChange([...controls, control]);
    setShowForm(false);
  }

  function updateControl(id: string, updates: Partial<Control>) {
    onChange(controls.map((c) => (c.id === id ? { ...c, ...updates } : c)));
  }

  function removeControl(id: string) {
    onChange(controls.filter((c) => c.id !== id));
  }

  return (
    <div className="controls-panel">
      <h3>Controls</h3>
      {controls.length === 0 && <p className="muted">No controls added yet.</p>}
      <ul>
        {controls.map((c) => {
          const target = basicEvents.find((e) => e.id === c.target_basic_event_id);
          return (
            <li key={c.id} className="control-row">
              <label>
                <input
                  type="checkbox"
                  checked={c.active}
                  onChange={(e) => updateControl(c.id, { active: e.target.checked })}
                />
                {c.description}
              </label>
              <span className="muted"> → {target?.description ?? c.target_basic_event_id}</span>
              <span className="muted"> ({Math.round(c.effectiveness * 100)}% effective)</span>
              <button type="button" onClick={() => removeControl(c.id)}>
                remove
              </button>
            </li>
          );
        })}
      </ul>

      {showForm ? (
        <ControlForm basicEvents={basicEvents} onSubmit={addControl} onCancel={() => setShowForm(false)} />
      ) : (
        <button type="button" onClick={() => setShowForm(true)} disabled={basicEvents.length === 0}>
          + Add control
        </button>
      )}
    </div>
  );
}
