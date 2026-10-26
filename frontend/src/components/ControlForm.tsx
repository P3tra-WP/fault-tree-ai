import { useState } from "react";
import type { BasicEvent, Control } from "../types";

interface ControlFormProps {
  basicEvents: BasicEvent[];
  onSubmit: (control: Control) => void;
  onCancel: () => void;
}

export function ControlForm({ basicEvents, onSubmit, onCancel }: ControlFormProps) {
  const [description, setDescription] = useState("");
  const [targetId, setTargetId] = useState(basicEvents[0]?.id ?? "");
  const [effectiveness, setEffectiveness] = useState(50);

  function submit() {
    if (!description.trim() || !targetId) return;
    onSubmit({
      id: `control_${Date.now().toString(36)}_${Math.floor(Math.random() * 1000)}`,
      description: description.trim(),
      target_basic_event_id: targetId,
      effectiveness: effectiveness / 100,
      active: true,
      rationale: null,
    });
  }

  return (
    <div className="control-form">
      <input
        placeholder="Control description, e.g. MFA"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <select value={targetId} onChange={(e) => setTargetId(e.target.value)}>
        {basicEvents.map((e) => (
          <option key={e.id} value={e.id}>
            {e.description}
          </option>
        ))}
      </select>
      <label>
        Effectiveness: {effectiveness}%
        <input
          type="range"
          min={0}
          max={100}
          value={effectiveness}
          onChange={(e) => setEffectiveness(Number(e.target.value))}
        />
      </label>
      <button type="button" onClick={submit}>
        Add
      </button>
      <button type="button" onClick={onCancel}>
        Cancel
      </button>
    </div>
  );
}
