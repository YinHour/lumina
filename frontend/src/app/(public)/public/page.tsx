'use client'
import { useState } from 'react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { PublicNotebooks } from './components/PublicNotebooks'
import { PublicSources } from './components/PublicSources'
import { Globe } from 'lucide-react'
import { Input } from '@/components/ui/input'

export default function PublicPage() {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [activeTab, setActiveTab] = useState<'notebooks' | 'sources'>('notebooks')

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 px-6 py-4 border-b">
        <Globe className="h-5 w-5 text-primary" />
        <h1 className="text-lg font-semibold">{t.public?.discover || 'Discover'}</h1>
      </div>

      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-5xl mx-auto space-y-6">
          <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
            <div className="flex gap-1 bg-muted rounded-lg p-1">
              <button
                onClick={() => setActiveTab('notebooks')}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  activeTab === 'notebooks'
                    ? 'bg-background shadow-sm text-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {t.public?.notebooks || 'Notebooks'}
              </button>
              <button
                onClick={() => setActiveTab('sources')}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  activeTab === 'sources'
                    ? 'bg-background shadow-sm text-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {t.public?.sources || 'Sources'}
              </button>
            </div>
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t.public?.searchPlaceholder || 'Search...'}
              className="w-full sm:w-72"
            />
          </div>

          {activeTab === 'notebooks' ? (
            <PublicNotebooks searchQuery={searchQuery} />
          ) : (
            <PublicSources searchQuery={searchQuery} />
          )}
        </div>
      </div>
    </div>
  )
}
