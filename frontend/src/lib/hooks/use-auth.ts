import { useCallback } from 'react'
import { useAuthStore } from '@/lib/stores/auth-store'
import { useRouter } from 'next/navigation'

export function useAuth() {
  const { login: storeLogin, logout: storeLogout, isLoading, error, isAuthenticated, username } = useAuthStore()
  const router = useRouter()

  const login = useCallback(
    async (username: string, password: string) => {
      const success = await storeLogin(username, password)
      if (success) {
        router.push('/notebooks')
      }
      return success
    },
    [storeLogin, router]
  )

  const logout = useCallback(() => {
    storeLogout()
    router.push('/')
  }, [storeLogout, router])

  return { login, logout, isLoading, error, isAuthenticated, username }
}
