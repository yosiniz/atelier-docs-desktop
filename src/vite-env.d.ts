/// <reference types="vite/client" />

interface Window {
  desktop?: {
    saveDialog: (options: { defaultPath: string; filters?: Array<{ name: string; extensions: string[] }> }) => Promise<{ canceled: boolean; filePath?: string }>
    writeFile: (targetPath: string, bytes: ArrayBuffer) => Promise<{ ok: boolean; size: number }>
    showItemInFolder: (targetPath: string) => Promise<void>
    platform: string
    apiBase: string
    apiToken: string
  }
}
