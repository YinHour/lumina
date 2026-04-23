import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { LoginForm } from './LoginForm'

vi.mock('@/lib/config', () => ({
  getConfig: vi.fn().mockResolvedValue({
    apiUrl: 'http://127.0.0.1:5055',
    version: 'test-version',
    buildTime: '2026-04-23T00:00:00.000Z',
  }),
}))

vi.mock('@/lib/hooks/use-auth', () => ({
  useAuth: () => ({
    login: vi.fn(),
    isLoading: false,
    error: null,
  }),
}))

vi.mock('@/lib/stores/auth-store', () => ({
  useAuthStore: () => ({
    authRequired: true,
    checkAuthRequired: vi.fn(),
    hasHydrated: true,
    isAuthenticated: false,
  }),
}))

describe('LoginForm', () => {
  it('uses the refreshed loginpage background, keeps it unscaled, places the card slightly lower, and renders a frameless panel with thicker light-black bordered square inputs', async () => {
    const { container } = render(<LoginForm />)

    const usernameInput = await screen.findByPlaceholderText('Username / Email / Researcher ID')
    const passwordInput = screen.getByPlaceholderText('Password')
    expect(screen.getByText('Remember me')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Forgot password?' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Register new account' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Show password' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Lumina' })).not.toBeInTheDocument()
    expect(screen.queryByText('Illuminating Discovery, Advancing Life.')).not.toBeInTheDocument()

    const pageShell = container.firstElementChild as HTMLElement
    expect(pageShell.getAttribute('style')).toContain('/images/loginpage-bg-new.png')
    expect(pageShell.getAttribute('style')).not.toContain('/images/loginpage-design.png')
    expect(pageShell.className).toContain('bg-center')
    expect(pageShell.className).toContain('bg-contain')

    const alignmentLayer = pageShell.querySelector('.justify-center') as HTMLElement
    expect(alignmentLayer.className).toContain('items-end')
    expect(alignmentLayer.className).toContain('pb-24')

    const panelWidth = Array.from(pageShell.querySelectorAll('div')).find((element) =>
      (element as HTMLElement).className.includes('max-w-[560px]')
    ) as HTMLElement | undefined
    expect(panelWidth).toBeDefined()

    const framelessPanel = Array.from(pageShell.querySelectorAll('div')).find((element) =>
      (element as HTMLElement).className.includes('px-7 py-7')
    ) as HTMLElement | undefined
    expect(framelessPanel).toBeDefined()
    expect(framelessPanel?.className).not.toContain('border ')
    expect(framelessPanel?.className).not.toContain('shadow-')
    expect(framelessPanel?.className).not.toContain('rounded-')

    const form = screen.getByRole('form', { name: 'Login form' })
    const submitButton = screen.getByRole('button', { name: 'Sign In' })
    expect(form.className).toContain('space-y-5')
    expect(submitButton.className).toContain('h-14')
    expect(submitButton.className).toContain('rounded-none')

    const usernameWrapper = usernameInput.parentElement as HTMLElement
    const passwordWrapper = passwordInput.parentElement as HTMLElement
    expect(usernameWrapper.className).toContain('rounded-none')
    expect(passwordWrapper.className).toContain('rounded-none')
    expect(usernameWrapper.className).toContain('border')
    expect(passwordWrapper.className).toContain('border')
    expect(usernameWrapper.className).toContain('border-2')
    expect(passwordWrapper.className).toContain('border-2')
    expect(usernameWrapper.className).toContain('border-black/35')
    expect(passwordWrapper.className).toContain('border-black/35')
  })
})
