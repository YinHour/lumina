'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiUrl } from '@/lib/config'

export function ForgotPasswordForm() {
  const { t } = useTranslation()
  const router = useRouter()

  // Step 1: enter email
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isSendingCode, setIsSendingCode] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [step, setStep] = useState<'email' | 'reset'>('email')
  const [countdown, setCountdown] = useState(0)
  const [success, setSuccess] = useState(false)

  const sendCode = useCallback(async () => {
    if (!email) return
    setIsSendingCode(true)
    setError(null)
    try {
      const apiUrl = await getApiUrl()
      const res = await fetch(`${apiUrl}/api/auth/send-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, purpose: 'reset_password' }),
      })
      const data = await res.json()
      if (res.ok && data.success) {
        setStep('reset')
        setCountdown(60)
        const timer = setInterval(() => {
          setCountdown((c) => {
            if (c <= 1) { clearInterval(timer); return 0 }
            return c - 1
          })
        }, 1000)
      } else {
        setError(data.message || 'Failed to send code')
      }
    } catch {
      setError('Network error. Please try again.')
    } finally {
      setIsSendingCode(false)
    }
  }, [email])

  const handleReset = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (password.length < 6) {
      setError(t.auth.registerPasswordTooShort)
      return
    }

    setIsLoading(true)
    try {
      const apiUrl = await getApiUrl()
      const res = await fetch(`${apiUrl}/api/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, code, new_password: password }),
      })
      const data = await res.json()
      if (res.ok && data.success) {
        setSuccess(true)
        setTimeout(() => router.push('/login'), 1500)
      } else {
        setError(data.message || t.auth.forgotPasswordError)
      }
    } catch {
      setError('Network error. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }, [email, code, password, router, t])

  if (success) {
    return (
      <div className="flex min-h-screen items-center justify-center" style={{
        background: 'radial-gradient(ellipse at 50% 0%, rgba(120,80,60,0.12) 0%, transparent 60%), #FAFAF8',
      }}>
        <div className="w-full max-w-md rounded-2xl border border-stone-200/60 bg-white/80 p-8 text-center shadow-xl backdrop-blur-sm">
          <div className="mb-4 text-5xl">✅</div>
          <h2 className="mb-2 text-2xl font-light text-stone-700">{t.auth.forgotPasswordSuccess}</h2>
          <p className="mt-4 text-sm text-stone-400">Redirecting to login...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center" style={{
      background: 'radial-gradient(ellipse at 50% 0%, rgba(120,80,60,0.12) 0%, transparent 60%), #FAFAF8',
    }}>
      <div className="w-full max-w-md rounded-2xl border border-stone-200/60 bg-white/80 p-8 shadow-xl backdrop-blur-sm">
        <div className="mb-8 text-center">
          <h1 className="mb-2 text-3xl font-light text-stone-700">{t.auth.forgotPasswordTitle}</h1>
          <p className="text-stone-500">{t.auth.forgotPasswordDesc}</p>
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600">
            {error}
          </div>
        )}

        {step === 'email' ? (
          <form onSubmit={(e) => { e.preventDefault(); sendCode() }} className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-stone-600">{t.auth.forgotPasswordEmailPlaceholder}</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t.auth.forgotPasswordEmailPlaceholder}
                required
                className="w-full rounded-lg border border-stone-300 bg-white/60 px-4 py-3 text-stone-700 placeholder-stone-400 shadow-sm transition focus:border-stone-400 focus:outline-none focus:ring-1 focus:ring-stone-400"
              />
            </div>
            <button
              type="submit"
              disabled={isSendingCode}
              className="w-full rounded-lg bg-stone-700 py-3 font-medium text-white shadow-md transition hover:bg-stone-800 disabled:opacity-50"
            >
              {isSendingCode ? t.auth.sendingCode : t.auth.forgotPasswordSendCodeButton}
            </button>
          </form>
        ) : (
          <form onSubmit={handleReset} className="space-y-4">
            <div className="rounded-lg bg-stone-50 p-3 text-sm text-stone-600">
              {t.auth.emailSent} <span className="font-medium">{email}</span>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-stone-600">{t.auth.forgotPasswordCodePlaceholder}</label>
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder={t.auth.forgotPasswordCodePlaceholder}
                required
                className="w-full rounded-lg border border-stone-300 bg-white/60 px-4 py-3 text-stone-700 placeholder-stone-400 shadow-sm transition focus:border-stone-400 focus:outline-none focus:ring-1 focus:ring-stone-400"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-stone-600">{t.auth.forgotPasswordNewPasswordPlaceholder}</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={t.auth.forgotPasswordNewPasswordPlaceholder}
                required
                minLength={6}
                className="w-full rounded-lg border border-stone-300 bg-white/60 px-4 py-3 text-stone-700 placeholder-stone-400 shadow-sm transition focus:border-stone-400 focus:outline-none focus:ring-1 focus:ring-stone-400"
              />
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="w-full rounded-lg bg-stone-700 py-3 font-medium text-white shadow-md transition hover:bg-stone-800 disabled:opacity-50"
            >
              {isLoading ? t.auth.resettingPassword : t.auth.forgotPasswordResetButton}
            </button>
            <div className="text-center">
              <button
                type="button"
                onClick={() => { setStep('email'); setCode(''); setPassword('') }}
                disabled={countdown > 0}
                className="text-sm text-stone-500 transition hover:text-stone-700 disabled:opacity-50"
              >
                {countdown > 0 ? `${countdown}s` : t.auth.backToLogin}
              </button>
            </div>
          </form>
        )}

        <div className="mt-6 text-center">
          <button
            type="button"
            onClick={() => router.push('/login')}
            className="text-stone-500 transition hover:text-stone-700"
          >
            {t.auth.backToLogin}
          </button>
        </div>
      </div>
    </div>
  )
}
