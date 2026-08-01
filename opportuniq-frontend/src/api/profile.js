import axios from 'axios'
import apiClient from './client'

const UPLOAD_TIMEOUT_MS = 15000

function getSafeErrorDetail(data) {
  if (typeof data?.detail === 'string') {
    return data.detail
  }

  const nestedMessage = data?.detail?.error?.message
  return typeof nestedMessage === 'string' ? nestedMessage : data?.message
}

export async function uploadResume(file) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await apiClient.post('/api/profile/upload', formData, {
    timeout: UPLOAD_TIMEOUT_MS,
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })

  return response.data
}

export async function createManualProfile(profile) {
  const response = await apiClient.post('/api/profile/manual', profile)
  return response.data
}

export async function getProfile(profileId) {
  const response = await apiClient.get(`/api/profile/${profileId}`)

  return response.data
}

export async function updateProfile(profileId, profile) {
  const response = await apiClient.patch(`/api/profile/${profileId}`, profile)

  return response.data
}

export function getProfileErrorMessage(error) {
  if (!error.response) {
    return 'Network failure. Please check your connection and try again.'
  }

  const status = error.response.status
  const detail = getSafeErrorDetail(error.response.data)

  if (status === 404) {
    return 'Profile not found. Please upload your resume again.'
  }

  if (status >= 500) {
    return 'Unexpected server error. Please try again later.'
  }

  return detail || 'Backend error. Please try again.'
}

export function getUploadErrorMessage(error) {
  if (error.code === 'ECONNABORTED') {
    return 'Request timeout. The upload took too long. Please try again.'
  }

  if (!error.response) {
    return 'Network failure. Please check your connection and try again.'
  }

  const status = error.response.status
  const responseData = error.response.data
  const detail = getSafeErrorDetail(responseData)
  const fallback = responseData?.fallback || responseData?.detail?.error?.fallback

  if (status === 400 || status === 415) {
    return detail || 'Unsupported file. Please upload a PDF, DOC or DOCX resume.'
  }

  if (status === 422) {
    return 'We could not extract a profile from this resume. Try another file or continue with manual setup.'
  }

  if (status === 503 && fallback === 'manual') {
    return 'AI resume extraction is currently unavailable. You can continue by setting up your profile manually.'
  }

  if (status === 504) {
    return 'Resume extraction is taking longer than expected. Please try again or continue with manual setup.'
  }

  if (status >= 500) {
    return 'Unexpected server error. Please try again later.'
  }

  return detail || 'Backend error. Please try again.'
}

export function isAxiosUploadError(error) {
  return axios.isAxiosError(error)
}
