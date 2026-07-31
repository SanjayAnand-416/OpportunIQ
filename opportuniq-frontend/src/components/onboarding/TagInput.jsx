import { X } from 'lucide-react'
import { useState } from 'react'

export default function TagInput({ id, label, value, onChange, disabled }) {
  const [draft, setDraft] = useState('')

  const addTag = () => {
    const nextTag = draft.trim()

    if (!nextTag || value.includes(nextTag)) {
      setDraft('')
      return
    }

    onChange([...value, nextTag])
    setDraft('')
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault()
      addTag()
    }

    if (event.key === 'Backspace' && !draft && value.length > 0) {
      onChange(value.slice(0, -1))
    }
  }

  const removeTag = (tagToRemove) => {
    onChange(value.filter((tag) => tag !== tagToRemove))
  }

  return (
    <div className="tag-input-wrap">
      <div className="tag-list" aria-label={`${label} list`}>
        {value.map((tag) => (
          <span className="tag-chip" key={tag}>
            {tag}
            <button
              type="button"
              onClick={() => removeTag(tag)}
              disabled={disabled}
              aria-label={`Remove ${tag}`}
            >
              <X size={14} aria-hidden="true" />
            </button>
          </span>
        ))}
        <input
          id={id}
          type="text"
          value={draft}
          onBlur={addTag}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="Type and press Enter"
          aria-label={label}
        />
      </div>
    </div>
  )
}
