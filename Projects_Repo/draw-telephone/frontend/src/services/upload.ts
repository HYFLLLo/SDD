import api from './api'
import type { ApiResponse, UploadImageResponse } from '../types'

/** POST /api/upload/image 上传画作图片 */
export async function uploadImage(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await api.post<ApiResponse<UploadImageResponse>>('/upload/image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}
