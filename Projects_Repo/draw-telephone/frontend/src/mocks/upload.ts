import type { ApiResponse, UploadImageResponse } from '../types'

/** POST /api/upload/image 上传响应 */
export const uploadImageResponse: ApiResponse<UploadImageResponse> = {
  code: 200,
  message: 'success',
  data: {
    url: '/mock-thumbs/uploaded.svg',
    size: 102400,
  },
}

/** POST /api/upload/image 格式不支持响应 */
export const uploadImageFailResponse: ApiResponse<null> = {
  code: 400,
  message: '文件格式不支持',
  data: null,
}
