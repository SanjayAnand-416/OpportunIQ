import axios from 'axios'
import apiClient from './client'

const UPLOAD_TIMEOUT_MS = 15000

export async function uploadResume(file) {
  const formData = new FormData()
  formData.append('resume', file)

  const response = await apiClient.post('/api/profile/upload', formData, {
    timeout: UPLOAD_TIMEOUT_MS,
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })

  return response.data
}

export function getUploadErrorMessage(error) {
  if (error.code === 'ECONNABORTED') {
    return 'Request timeout. The upload took too long. Please try again.'
  }

  if (!error.response) {
    return 'Network failure. Please check your connection and try again.'
  }

  const status = error.response.status
  const detail = error.response.data?.detail || error.response.data?.message

  if (status === 400 || status === 415) {
    return detail || 'Unsupported file. Please upload a PDF, DOC or DOCX resume.'
  }

  if (status === 422) {
    return detail || 'ResumeAI extraction failed. Please try another resume or set up manually.'
  }

  if (status >= 500) {
    return 'Unexpected server error. Please try again later.'
  }

  return detail || 'Backend error. Please try again.'
}

export function isAxiosUploadError(error) {
  return axios.isAxiosError(error)
}
