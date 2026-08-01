export default function ToggleSwitch({ checked, disabled, id, label, onChange }) {
  return (
    <label className="settings-toggle" htmlFor={id}>
      <span>{label}</span>
      <input
        id={id}
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span className="settings-toggle-track" aria-hidden="true">
        <span />
      </span>
    </label>
  )
}

