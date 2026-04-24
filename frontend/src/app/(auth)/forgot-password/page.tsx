import { ForgotPasswordForm } from '@/components/auth/ForgotPasswordForm'
import { ErrorBoundary } from '@/components/common/ErrorBoundary'

export default function ForgotPasswordPage() {
  return (
    <ErrorBoundary>
      <ForgotPasswordForm />
    </ErrorBoundary>
  )
}
