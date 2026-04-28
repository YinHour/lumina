'use client'

import { useTranslation } from '@/lib/hooks/use-translation'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'
import { Lock, Globe } from 'lucide-react'

export type Visibility = 'private' | 'public'

interface VisibilitySelectorProps {
  value: Visibility
  onChange: (visibility: Visibility) => void
  className?: string
}

export function VisibilitySelector({ value, onChange, className }: VisibilitySelectorProps) {
  const { t } = useTranslation()

  const options: { value: Visibility; icon: typeof Lock; label: string; description: string }[] = [
    {
      value: 'private',
      icon: Lock,
      label: t.visibility.private,
      description: t.visibility.privateDesc,
    },
    {
      value: 'public',
      icon: Globe,
      label: t.visibility.public,
      description: t.visibility.publicDesc,
    },
  ]

  return (
    <div className={cn('space-y-2', className)}>
      <Label>{t.visibility.label}</Label>
      <div className="grid grid-cols-2 gap-2">
        {options.map(({ value: optValue, icon: Icon, label, description }) => (
          <button
            key={optValue}
            type="button"
            onClick={() => onChange(optValue)}
            className={cn(
              'flex flex-col items-start gap-1.5 p-3 rounded-lg border text-left transition-all',
              'hover:bg-accent/50 focus:outline-none focus:ring-2 focus:ring-primary/50',
              value === optValue
                ? 'border-primary bg-primary/5 ring-1 ring-primary'
                : 'border-border hover:border-primary/50'
            )}
          >
            <div className="flex items-center gap-2">
              <Icon className="h-4 w-4 text-primary" />
              <span className="text-sm font-medium">{label}</span>
            </div>
            <span className="text-xs text-muted-foreground leading-relaxed">
              {description}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
