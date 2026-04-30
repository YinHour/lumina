import apiClient from './client'
import type { EmbedRequest, EmbedResponse } from '../types/generated-api'

export type EmbedContentRequest = Omit<EmbedRequest, 'item_type'> & {
  item_type: 'source' | 'note'
}

export type EmbedContentResponse = EmbedResponse

export interface RebuildEmbeddingsRequest {
  mode: 'existing' | 'all'
  include_sources?: boolean
  include_notes?: boolean
  include_insights?: boolean
}

export interface RebuildEmbeddingsResponse {
  command_id: string
  message: string
  estimated_items: number
}

export interface RebuildProgress {
  total_items?: number
  processed_items?: number
  failed_items?: number
  total?: number
  processed?: number
  percentage?: number
}

export interface RebuildStats {
  sources_processed?: number
  notes_processed?: number
  insights_processed?: number
  sources?: number
  notes?: number
  insights?: number
  failed?: number
  failed_items?: number
  processing_time?: number
}

export interface RebuildStatusResponse {
  command_id: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  progress?: RebuildProgress
  stats?: RebuildStats
  started_at?: string
  completed_at?: string
  error_message?: string
}

export const embeddingApi = {
  embedContent: async (itemId: string, itemType: 'source' | 'note', asyncProcessing = false): Promise<EmbedContentResponse> => {
    const payload: EmbedContentRequest = {
      item_id: itemId,
      item_type: itemType,
      async_processing: asyncProcessing
    }
    const response = await apiClient.post<EmbedContentResponse>('/embed', payload)
    return response.data
  },

  rebuildEmbeddings: async (request: RebuildEmbeddingsRequest): Promise<RebuildEmbeddingsResponse> => {
    const response = await apiClient.post<RebuildEmbeddingsResponse>('/embeddings/rebuild', request)
    return response.data
  },

  getRebuildStatus: async (commandId: string): Promise<RebuildStatusResponse> => {
    const response = await apiClient.get<RebuildStatusResponse>(`/embeddings/rebuild/${commandId}/status`)
    return response.data
  }
}
