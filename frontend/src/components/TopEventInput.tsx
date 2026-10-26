interface TopEventInputProps {
  value: string;
  onChange: (value: string) => void;
}

export function TopEventInput({ value, onChange }: TopEventInputProps) {
  return (
    <div className="field">
      <label>Top Event — the one disaster you can't allow</label>
      <input
        type="text"
        placeholder="e.g. Agent triggers an irreversible production action"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
