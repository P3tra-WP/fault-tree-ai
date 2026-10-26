interface AttachPointPickerProps {
  onCancel: () => void;
}

export function AttachPointPicker({ onCancel }: AttachPointPickerProps) {
  return (
    <div className="attach-point-picker">
      <p>
        Click <strong>attach here</strong> on the gate below where the imported subtree should be
        added.
      </p>
      <button type="button" onClick={onCancel}>
        Cancel merge
      </button>
    </div>
  );
}
