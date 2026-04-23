import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ChangePasswordForm } from './ChangePasswordForm'

vi.mock('@/lib/hooks/use-toast', () => ({
  useToast: () => ({ toast: vi.fn() }),
}))

vi.mock('@/lib/hooks/use-change-password', () => ({
  useChangePassword: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    error: null,
  }),
}))

describe('ChangePasswordForm', () => {
  it('renders current/new/confirm password fields and submit button', () => {
    render(<ChangePasswordForm />)

    expect(screen.getByPlaceholderText('Current Password')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('New Password')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Confirm New Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Change Password' })).toBeInTheDocument()
  })
})
