import { useState } from 'react'
import ResumeUploadCard from '../components/onboarding/ResumeUploadCard'
import StepIndicator from '../components/onboarding/StepIndicator'
import { validateResumeFile } from '../utils/helpers'

const onboardingSteps = [
  { label: 'Upload Resume' },
  { label: 'Review Profile' },
  { label: 'Discover Opportunities' },
]

const uploadInputId = 'resume-upload-input'

export default function ResumeUpload() {
  const [uploadState, setUploadState] = useState('idle')
  const [selectedFile, setSelectedFile] = useState(null)
  const [error, setError] = useState('')

  const handleFile = (file) => {
    const validationError = validateResumeFile(file)

    if (validationError) {
      setSelectedFile(null)
      setError(validationError)
      setUploadState('error')
      return
    }

    setSelectedFile(file)
    setError('')
    setUploadState('selected')
  }

  const handleFileChange = (event) => {
    handleFile(event.target.files?.[0])
    event.target.value = ''
  }

  const handleDragEnter = (event) => {
    event.preventDefault()
    setUploadState('dragging')
  }

  const handleDragLeave = (event) => {
    event.preventDefault()
    setUploadState(selectedFile ? 'selected' : 'idle')
  }

  const handleDragOver = (event) => {
    event.preventDefault()
  }

  const handleDrop = (event) => {
    event.preventDefault()
    handleFile(event.dataTransfer.files?.[0])
  }

  const handleRemoveFile = () => {
    setSelectedFile(null)
    setError('')
    setUploadState('idle')
  }

  const handleDismissError = () => {
    setError('')
    setUploadState(selectedFile ? 'selected' : 'idle')
  }

  return (
    <main className="resume-page">
      <div className="resume-page-inner">
        <StepIndicator steps={onboardingSteps} activeStep={1} />
        <ResumeUploadCard
          error={error}
          inputId={uploadInputId}
          isDragging={uploadState === 'dragging'}
          selectedFile={selectedFile}
          onDismissError={handleDismissError}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onFileChange={handleFileChange}
          onRemoveFile={handleRemoveFile}
        />
        <section className="upload-info" aria-label="Upload instructions">
          <h2>Upload Instructions</h2>
          <p>
            Choose the most recent version of your resume so your profile can
            later be reviewed with accurate skills, experience and education.
          </p>
        </section>
        <section className="file-support" aria-label="Supported file information">
          <span>Supported files: PDF, DOC, DOCX</span>
          <span>Maximum file size: 5 MB</span>
        </section>
      </div>
    </main>
  )
}
