import { create } from 'zustand'
import * as authService from '../services/auth'
import type { LoginRequest, RegisterRequest, User } from '../types'

interface AuthState {
  token: string | null
  user: User | null
  loginStatus: 'idle' | 'loading' | 'success' | 'error'
  login: (data: LoginRequest) => Promise<void>
  register: (data: RegisterRequest) => Promise<void>
  logout: () => void
}

const TOKEN_KEY = 'token'
const USER_KEY = 'user'

function readStoredUser(): User | null {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw) as User) : null
  } catch {
    return null
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem(TOKEN_KEY),
  user: readStoredUser(),
  loginStatus: 'idle',

  login: async (data) => {
    set({ loginStatus: 'loading' })
    try {
      const res = await authService.login(data)
      localStorage.setItem(TOKEN_KEY, res.data.access_token)
      localStorage.setItem(USER_KEY, JSON.stringify(res.data.user))
      set({ token: res.data.access_token, user: res.data.user, loginStatus: 'success' })
    } catch (error) {
      set({ loginStatus: 'error' })
      throw error
    }
  },

  register: async (data) => {
    set({ loginStatus: 'loading' })
    try {
      const res = await authService.register(data)
      localStorage.setItem(TOKEN_KEY, res.data.access_token)
      localStorage.setItem(USER_KEY, JSON.stringify(res.data.user))
      set({ token: res.data.access_token, user: res.data.user, loginStatus: 'success' })
    } catch (error) {
      set({ loginStatus: 'error' })
      throw error
    }
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    set({ token: null, user: null, loginStatus: 'idle' })
  },
}))
