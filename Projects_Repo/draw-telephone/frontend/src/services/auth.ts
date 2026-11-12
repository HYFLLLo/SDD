import api from './api'
import type { ApiResponse, AuthResponse, LoginRequest, RegisterRequest } from '../types'

/** POST /api/auth/login */
export async function login(data: LoginRequest) {
  const res = await api.post<ApiResponse<AuthResponse>>('/auth/login', data)
  return res.data
}

/** POST /api/auth/register */
export async function register(data: RegisterRequest) {
  const res = await api.post<ApiResponse<AuthResponse>>('/auth/register', data)
  return res.data
}
