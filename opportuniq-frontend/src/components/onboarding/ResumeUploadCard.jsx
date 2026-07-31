import { CheckCircle2, FileText, Loader2, Upload, X } from 'lucide-react'
import { useRef } from 'react'
import ErrorBanner from '../common/ErrorBanner'
import { formatFileSize } from '../../utils/helpers'

export default function ResumeUploadCard({
  error,
  inputId,
  isDragging,
  isProcessing,
  selectedFile,
  uploadState,
  onBrowse,
  onDismissError,
  onDragEnter,
  onDragLeave,
  onDragOver,
  onDrop,
  onFileChange,
  onManualSetup,
  onRemoveFile,
  onUploadResume,
}) {
  const inputRef = useRef(null)
  const isUploading = uploadState === 'uploading'
  const isParsing = uploadState === 'parsing'
  const isSuccess = uploadState === 'success'

  const handleBrowse = () => {
    if (isProcessing) {
      return
    }

    inputRef.current?.click()
    onBrowse?.()
  }

  return (
    <section className="upload-card" aria-labelledby="resume-upload-title">
      <div className="upload-card-header">
        <div className="upload-card-icon">
          <Upload size={26} aria-hidden="true" />
        </div>
        <h1 id="resume-upload-title">Upload Your Resume</h1>
        <p>
          Upload your PDF, DOC or DOCX resume and let OpportunIQ automatically
          build your profile using AI.
        </p>
      </div>

      <ErrorBanner message={error} onDismiss={onDismissError} />

      <input
        ref={inputRef}
        id={inputId}
        className="sr-only"
        type="file"
        accept=".pdf,.doc,.docx"
        onChange={onFileChange}
        disabled={isProcessing}
      />

      {selectedFile ? (
        <div className="selected-file">
          <div className="selected-file-main">
            <div className="selected-file-icon">
              <CheckCircle2 size={24} aria-hidden="true" />
            </div>
            <div>
              <p className="selected-file-name">{selectedFile.name}</p>
              <p className="selected-file-size">
                {formatFileSize(selectedFile.size)}
              </p>
            </div>
          </div>
          <div className="selected-file-actions">
            <button
              type="button"
              className="upload-secondary-button"
              onClick={onRemoveFile}
              disabled={isProcessing}
              aria-label="Remove selected file"
            >
              <X size={16} aria-hidden="true" />
              Remove
            </button>
            <button
              type="button"
              className="upload-primary-button"
              onClick={handleBrowse}
              disabled={isProcessing}
              aria-label="Change selected resume file"
            >
              Change File
            </button>
          </div>

          <div className="upload-submit-area">
            {isUploading && (
              <div className="upload-status" aria-live="polite">
                <Loader2 className="spinner" size={20} aria-hidden="true" />
                Uploading your resume...
              </div>
            )}

            {isParsing && (
              <div className="upload-status" aria-live="polite">
                <Loader2 className="spinner" size={20} aria-hidden="true" />
                Extracting your profile with AI...
              </div>
            )}

            {isSuccess && (
              <div className="upload-success" aria-live="polite">
                <CheckCircle2 size={22} aria-hidden="true" />
                <div>
                  <p>Resume uploaded successfully</p>
                  <span>Preparing your profile...</span>
                </div>
              </div>
            )}

            {!isUploading && !isParsing && !isSuccess && (
              <button
                type="button"
                className="upload-resume-button"
                onClick={onUploadResume}
                disabled={!selectedFile || isProcessing}
                aria-label="Upload selected resume"
              >
                Upload Resume
              </button>
            )}
          </div>
        </div>
      ) : (
        <button
          type="button"
          className={`drop-zone ${isDragging ? 'drop-zone-active' : ''}`}
          onClick={handleBrowse}
          onDragEnter={onDragEnter}
          onDragLeave={onDragLeave}
          onDragOver={onDragOver}
          onDrop={onDrop}
          disabled={isProcessing}
          aria-label="Drag and drop your resume or click to browse files"
        >
          <span className="drop-zone-icon">
            <FileText size={30} aria-hidden="true" />
          </span>
          <span className="drop-zone-title">Drag & Drop your Resume</span>
          <span className="drop-zone-subtitle">or click to browse files</span>
          <span className="drop-zone-meta">PDF • DOC • DOCX</span>
          <span className="drop-zone-meta">Maximum size: 5 MB</span>
        </button>
      )}

      {uploadState === 'error' && (
        <div className="manual-fallback">
          <button
            type="button"
            className="upload-secondary-button"
            onClick={onManualSetup}
            aria-label="Set up profile manually"
          >
            Set Up Manually
          </button>
        </div>
      )}
    </section>
  )
}
