import apiClient from './client'

export interface ChangePasswordRequest {
  old_password: string
  new_password: string
}

export interface ChangePasswordResponse {
  success: boolean
  message: string
}

export const authApi = {
  changePassword: async (data: ChangePasswordRequest) => {
    const response = await apiClient.post<ChangePasswordResponse>('/auth/change-password', data)
    return response.data
  },
}
