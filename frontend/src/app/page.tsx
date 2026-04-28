'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth-store'
import { HomePageContent } from '@/components/home/HomePageContent'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'

export default function HomePage() {
  const router = useRouter()
  const { hasHydrated, isAuthenticated, token } = useAuthStore()
  const [shouldRedirect, setShouldRedirect] = useState(false)

  useEffect(() => {
    if (!hasHydrated) return

    // Authenticated users (including guest mode with token='not-required') → dashboard
    if (isAuthenticated && token) {
      setShouldRedirect(true)
      router.replace('/notebooks')
    }
  }, [hasHydrated, isAuthenticated, token, router])

  // Show spinner while zustand is rehydrating from localStorage
  if (!hasHydrated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner />
      </div>
    )
  }

  // While redirecting, show spinner to avoid flash
  if (shouldRedirect) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner />
      </div>
    )
  }

  // Not authenticated → show product homepage
  return <HomePageContent />
}
