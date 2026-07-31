import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  getUploadErrorMessage,
  isAxiosUploadError,
  uploadResume,
} from '../api/profile'
import ResumeUploadCard from '../components/onboarding/ResumeUploadCard'
import StepIndicator from '../components/onboarding/StepIndicator'
import { ROUTES } from '../constants/routes'
import { validateResumeFile } from '../utils/helpers'

const onboardingSteps = [
  { label: 'Upload Resume' },
  { label: 'Review Profile' },
  { label: 'Discover Opportunities' },
]

const uploadInputId = 'resume-upload-input'
const createDelay = (milliseconds) =>
  new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds)
  })

export default function ResumeUpload() {
  const navigate = useNavigate()
  const [uploadState, setUploadState] = useState('idle')
  const [selectedFile, setSelectedFile] = useState(null)
  const [error, setError] = useState('')

  const isProcessing =
    uploadState === 'uploading' ||
    uploadState === 'parsing' ||
    uploadState === 'success'

  const handleFile = (file) => {
    if (isProcessing) {
      return
    }

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
    if (isProcessing) {
      return
    }
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
    if (isProcessing) {
      return
    }
    handleFile(event.dataTransfer.files?.[0])
  }

  const handleRemoveFile = () => {
    if (isProcessing) {
      return
    }

    setSelectedFile(null)
    setError('')
    setUploadState('idle')
  }

  const handleDismissError = () => {
    setError('')
    setUploadState(selectedFile ? 'selected' : 'idle')
  }

  const handleManualSetup = () => {
    navigate(ROUTES.MANUAL)
  }

  const handleUploadResume = async () => {
    if (!selectedFile || isProcessing) {
      return
    }

    setError('')
    setUploadState('uploading')

    try {
      const data = await uploadResume(selectedFile)
      setUploadState('parsing')
      await createDelay(600)

      const profileId = data?.profile_id

      if (!profileId) {
        setError('Unexpected server error. Missing profile details in response.')
        setUploadState('error')
        return
      }

      setUploadState('success')

      window.setTimeout(() => {
        navigate(
          `${ROUTES.PROFILE_REVIEW}?profile_id=${encodeURIComponent(profileId)}`,
        )
      }, 1000)
    } catch (requestError) {
      const message = isAxiosUploadError(requestError)
        ? getUploadErrorMessage(requestError)
        : 'Unexpected server error. Please try again later.'

      setError(message)
      setUploadState('error')
    }
  }

  return (
    <main className="resume-page">
      <div className="resume-page-inner">
        <StepIndicator steps={onboardingSteps} activeStep={1} />
        <ResumeUploadCard
          error={error}
          inputId={uploadInputId}
          isDragging={uploadState === 'dragging'}
          isProcessing={isProcessing}
          selectedFile={selectedFile}
          uploadState={uploadState}
          onDismissError={handleDismissError}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onFileChange={handleFileChange}
          onManualSetup={handleManualSetup}
          onRemoveFile={handleRemoveFile}
          onUploadResume={handleUploadResume}
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
