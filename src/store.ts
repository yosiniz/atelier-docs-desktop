import { create } from 'zustand'
import type { UploadedDocument } from './types'

type AppState = {
  document: UploadedDocument | null
  setDocument: (document: UploadedDocument | null) => void
  theme: 'dark' | 'light'
  toggleTheme: () => void
}

export const useAppStore = create<AppState>((set) => ({
  document: null,
  setDocument: (document) => set({ document }),
  theme: 'dark',
  toggleTheme: () => set((state) => ({ theme: state.theme === 'dark' ? 'light' : 'dark' })),
}))
