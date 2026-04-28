"use client"

import { Control, Controller, useWatch } from "react-hook-form"
import { useTranslation } from "@/lib/hooks/use-translation"
import { FormSection } from "@/components/ui/form-section"
import { CheckboxList } from "@/components/ui/checkbox-list"
import { Checkbox } from "@/components/ui/checkbox"
import { VisibilitySelector } from "@/components/notebooks/VisibilitySelector"
import { Transformation } from "@/lib/types/transformations"
import { SettingsResponse } from "@/lib/types/api"

interface CreateSourceFormData {
  type: 'link' | 'upload' | 'text'
  title?: string
  url?: string
  content?: string
  file?: FileList | File
  notebooks?: string[]
  transformations?: string[]
  embed: boolean
  async_processing: boolean
  visibility: 'private' | 'public'
}

interface ProcessingStepProps {
  control: Control<CreateSourceFormData>
  transformations: Transformation[]
  selectedTransformations: string[]
  onToggleTransformation: (transformationId: string) => void
  loading?: boolean
  settings?: SettingsResponse
}

export function ProcessingStep({
  control,
  transformations,
  selectedTransformations,
  onToggleTransformation,
  loading = false,
  settings
}: ProcessingStepProps) {
  const { t } = useTranslation()
  const transformationItems = transformations.map((transformation) => ({
    id: transformation.id,
    title: transformation.title,
    description: transformation.description
  }))

  // Watch visibility from form
  const visibility = useWatch({ control, name: 'visibility' }) as 'private' | 'public'

  return (
    <div className="space-y-8">
      {/* Visibility selector */}
      <FormSection
        title={t.visibility?.title || 'Visibility'}
        description={t.visibility?.description || 'Control who can see this source'}
      >
        <Controller
          control={control}
          name="visibility"
          render={({ field }) => (
            <VisibilitySelector
              value={field.value}
              onChange={field.onChange}
            />
          )}
        />
      </FormSection>

      <FormSection
        title={`${t.navigation.transformations} (${t.common.optional})`}
        description={t.sources.processDescription}
      >
        <CheckboxList
          items={transformationItems}
          selectedIds={selectedTransformations}
          onToggle={onToggleTransformation}
          loading={loading}
          emptyMessage={t.common.noMatches}
        />
      </FormSection>

      <FormSection
        title={t.navigation.settings}
        description={t.sources.processDescription}
      >
        <div className="space-y-4">
          {settings?.default_embedding_option === 'ask' && (
            <Controller
              control={control}
              name="embed"
              render={({ field }) => (
                <label 
                  htmlFor="enable-embedding"
                  className="flex items-start gap-3 cursor-pointer p-3 rounded-md hover:bg-muted"
                >
                  <Checkbox
                    id="enable-embedding"
                    checked={field.value}
                    onCheckedChange={field.onChange}
                    className="mt-0.5"
                  />
                  <div className="flex-1">
                    <span className="text-sm font-medium block">{t.sources.enableEmbedding}</span>
                    <p className="text-xs text-muted-foreground mt-1">
                      {t.sources.embeddingDesc}
                    </p>
                  </div>
                </label>
              )}
            />
          )}

          {settings?.default_embedding_option === 'always' && (
            <div className="p-3 rounded-md bg-primary/10 border border-primary/30">
              <div className="flex items-start gap-3">
                <div className="w-4 h-4 bg-primary rounded-full mt-0.5 flex-shrink-0"></div>
                <div className="flex-1">
                  <span className="text-sm font-medium block text-primary">{t.sources.embeddingAlways}</span>
                  <p className="text-xs text-primary mt-1">
                    {t.sources.embeddingAlwaysDesc}
                    {t.sources.changeInSettings} <span className="font-medium">{t.navigation.settings}</span>.
                  </p>
                </div>
              </div>
            </div>
          )}

          {settings?.default_embedding_option === 'never' && (
            <div className="p-3 rounded-md bg-muted border border-border">
              <div className="flex items-start gap-3">
                <div className="w-4 h-4 bg-muted-foreground rounded-full mt-0.5 flex-shrink-0"></div>
                <div className="flex-1">
                  <span className="text-sm font-medium block text-foreground">{t.sources.embeddingNever}</span>
                  <p className="text-xs text-muted-foreground mt-1">
                    {t.sources.embeddingNeverDesc}
                    {t.sources.changeInSettings} <span className="font-medium">{t.navigation.settings}</span>.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </FormSection>
    </div>
  )
}
