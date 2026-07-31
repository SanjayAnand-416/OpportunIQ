import { Loader2 } from 'lucide-react'
import { hasValue } from '../../utils/helpers'
import FieldStatusBadge from './FieldStatusBadge'
import TagInput from './TagInput'

const alwaysNeedsInput = ['email', 'degree', 'college']

const fields = [
  { name: 'fullName', label: 'Full Name', type: 'text' },
  { name: 'email', label: 'Email', type: 'email' },
  { name: 'degree', label: 'Degree', type: 'text' },
  { name: 'college', label: 'College', type: 'text' },
  { name: 'yearOfStudy', label: 'Year of Study', type: 'text' },
  { name: 'preferredLocation', label: 'Preferred Location', type: 'text' },
  { name: 'opportunityType', label: 'Opportunity Type', type: 'text' },
]

function getFieldStatus(fieldName, value) {
  if (alwaysNeedsInput.includes(fieldName)) {
    return 'needed'
  }

  return hasValue(value) ? 'confirmed' : 'needed'
}

export default function ProfileReviewForm({
  isSubmitting,
  isSubmitDisabled,
  profile,
  onChange,
  onSubmit,
}) {
  const handleInputChange = (event) => {
    onChange(event.target.name, event.target.value)
  }

  return (
    <section className="profile-form-card" aria-labelledby="profile-review-title">
      <div className="profile-form-header">
        <p>Step 2</p>
        <h1 id="profile-review-title">Review Your Profile</h1>
        <span>
          Confirm the details extracted from your resume and complete anything
          missing before discovery begins.
        </span>
      </div>

      <form className="profile-form" onSubmit={onSubmit}>
        {fields.map((field) => (
          <div className="form-field" key={field.name}>
            <div className="field-label-row">
              <label htmlFor={field.name}>{field.label}</label>
              <FieldStatusBadge
                status={getFieldStatus(field.name, profile[field.name])}
              />
            </div>
            <input
              id={field.name}
              name={field.name}
              type={field.type}
              value={profile[field.name]}
              onChange={handleInputChange}
              disabled={isSubmitting}
              autoComplete={field.type === 'email' ? 'email' : 'off'}
            />
          </div>
        ))}

        <div className="form-field">
          <div className="field-label-row">
            <label htmlFor="skills">Skills</label>
            <FieldStatusBadge status={getFieldStatus('skills', profile.skills)} />
          </div>
          <TagInput
            id="skills"
            label="Skills"
            value={profile.skills}
            onChange={(value) => onChange('skills', value)}
            disabled={isSubmitting}
          />
        </div>

        <div className="form-field">
          <div className="field-label-row">
            <label htmlFor="targetRoles">Target Roles</label>
            <FieldStatusBadge
              status={getFieldStatus('targetRoles', profile.targetRoles)}
            />
          </div>
          <TagInput
            id="targetRoles"
            label="Target Roles"
            value={profile.targetRoles}
            onChange={(value) => onChange('targetRoles', value)}
            disabled={isSubmitting}
          />
        </div>

        <button
          type="submit"
          className="confirm-profile-button"
          disabled={isSubmitDisabled}
          aria-label="Confirm profile and find opportunities"
        >
          {isSubmitting && (
            <Loader2 className="spinner" size={18} aria-hidden="true" />
          )}
          {isSubmitting
            ? 'Saving Profile...'
            : 'Confirm Profile & Find Opportunities'}
        </button>
      </form>
    </section>
  )
}
