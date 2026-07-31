const ALLOWED_RESUME_EXTENSIONS = ['.pdf', '.doc', '.docx']
const MAX_RESUME_SIZE_BYTES = 5 * 1024 * 1024

export function formatFileSize(bytes) {
  if (!bytes) {
    return '0 KB'
  }

  const megabytes = bytes / (1024 * 1024)

  if (megabytes >= 1) {
    return `${megabytes.toFixed(1)} MB`
  }

  return `${Math.max(1, Math.round(bytes / 1024))} KB`
}

export function validateResumeFile(file) {
  if (!file) {
    return 'No file selected.'
  }

  const fileName = file.name.toLowerCase()
  const isAllowedType = ALLOWED_RESUME_EXTENSIONS.some((extension) =>
    fileName.endsWith(extension),
  )

  if (!isAllowedType) {
    return 'Unsupported file type. Please upload a PDF, DOC or DOCX resume.'
  }

  if (file.size > MAX_RESUME_SIZE_BYTES) {
    return 'Maximum file size exceeded (5 MB).'
  }

  return ''
}
