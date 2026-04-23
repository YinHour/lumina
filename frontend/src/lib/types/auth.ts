export interface AuthState {
  isAuthenticated: boolean
  token: string | null
  username: string | null
  isLoading: boolean
  error: string | null
}

export interface LoginCredentials {
  username: string
  password: string
}

export interface AuthStatus {
  auth_enabled: boolean
  auth_method: 'legacy' | 'database' | 'disabled'
  has_users: boolean
  message: string
}

export interface LoginResponse {
  success: boolean
  token?: string
  username?: string
  message: string
}
