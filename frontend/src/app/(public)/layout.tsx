'use client'

import { ErrorBoundary } from '@/components/common/ErrorBoundary'
import { ModalProvider } from '@/components/providers/ModalProvider'
import { CreateDialogsProvider } from '@/lib/hooks/use-create-dialogs'
import { AppShell } from '@/components/layout/AppShell'

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ErrorBoundary>
      <CreateDialogsProvider>
        <AppShell>
          {children}
        </AppShell>
        <ModalProvider />
      </CreateDialogsProvider>
    </ErrorBoundary>
  )
}
