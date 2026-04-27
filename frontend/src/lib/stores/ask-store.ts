import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface StrategyData {
  reasoning: string
  searches: Array<{ term: string; instructions: string }>
}

interface AskState {
  isStreaming: boolean
  strategy: StrategyData | null
  answers: string[]
  finalAnswer: string | null
  error: string | null
  abortController: AbortController | null
  
  setStreaming: (isStreaming: boolean) => void
  setStrategy: (strategy: StrategyData | null) => void
  updateStrategyReasoning: (chunk: string) => void
  addAnswer: (answer: string) => void
  setFinalAnswer: (answer: string) => void
  setError: (error: string | null) => void
  setAbortController: (controller: AbortController | null) => void
  clearState: () => void
}

export const useAskStore = create<AskState>()(
  persist(
    (set, get) => ({
      isStreaming: false,
      strategy: null,
      answers: [],
      finalAnswer: null,
      error: null,
      abortController: null,

      setStreaming: (isStreaming) => set({ isStreaming }),
      setStrategy: (strategy) => set({ strategy }),
      updateStrategyReasoning: (chunk) => set((state) => ({
        strategy: {
          reasoning: (state.strategy?.reasoning || '') + chunk,
          searches: state.strategy?.searches || []
        }
      })),
      addAnswer: (answer) => set((state) => ({
        answers: [...state.answers, answer]
      })),
      setFinalAnswer: (finalAnswer) => set({ finalAnswer, isStreaming: false }),
      setError: (error) => set({ error, isStreaming: false }),
      setAbortController: (controller) => set({ abortController: controller }),
      clearState: () => {
        const { abortController } = get()
        if (abortController) {
          abortController.abort()
        }
        set({
          isStreaming: false,
          strategy: null,
          answers: [],
          finalAnswer: null,
          error: null,
          abortController: null
        })
      }
    }),
    {
      name: 'ask-store-state',
      partialize: (state) => ({
        strategy: state.strategy,
        answers: state.answers,
        finalAnswer: state.finalAnswer,
        error: state.error
        // Exclude isStreaming and abortController
      })
    }
  )
)
