import type { PdfInfo, TextBlock, UploadedDocument } from '../types'

const API_BASE = window.desktop?.apiBase || 'http://127.0.0.1:8765/api'
const API_TOKEN = window.desktop?.apiToken || ''

function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  if (API_TOKEN) headers.set('X-Atelier-Token', API_TOKEN)
  return fetch(`${API_BASE}${path}`, { ...init, headers })
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json()
    return body.detail || body.error?.message || 'İşlem başarısız oldu'
  } catch {
    return `İşlem başarısız oldu (${response.status})`
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(path, init)
  if (!response.ok) throw new Error(await errorMessage(response))
  const body = await response.json()
  return body.data as T
}

export async function upload(file: File): Promise<UploadedDocument> {
  const form = new FormData()
  form.append('file', file)
  return request<UploadedDocument>('/files', { method: 'POST', body: form })
}

export const renderUrl = (id: string, page: number, cacheKey: number) =>
  `${API_BASE}/pdf/${id}/pages/${page}/render?scale=2&v=${cacheKey}${API_TOKEN ? `&api_token=${encodeURIComponent(API_TOKEN)}` : ''}`

export const fileUrl = (id: string) =>
  `${API_BASE}/files/${id}/download${API_TOKEN ? `?api_token=${encodeURIComponent(API_TOKEN)}` : ''}`

export const getTextBlocks = (id: string, page: number) =>
  request<TextBlock[]>(`/pdf/${id}/pages/${page}/text`)

export interface PdfImageElement {
  id: string
  xref: number
  bbox: [number, number, number, number]
  pixel_width: number
  pixel_height: number
}

export const getPdfImages = (id: string, page: number) =>
  request<PdfImageElement[]>(`/pdf/${id}/pages/${page}/images`)

export const movePdfImage = (id: string, payload: unknown) =>
  request<PdfInfo>(`/pdf/${id}/content/image/move`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  })

export const editText = (id: string, payload: unknown) =>
  request<{ audit: { method: string }; pdf: PdfInfo }>(`/pdf/${id}/edit-text`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  })

export interface PdfSearchMatch {
  page: number
  bbox: number[]
  text: string
}

export const searchPdfText = (id: string, query: string, caseSensitive = false, wholeWord = false) =>
  request<{ matches: PdfSearchMatch[]; count: number }>(
    `/pdf/${id}/search?query=${encodeURIComponent(query)}&case_sensitive=${caseSensitive}&whole_word=${wholeWord}`,
  )

export const replacePdfText = (id: string, payload: unknown) =>
  request<{ audit: { matches: number; pages_changed: number; method: string }; pdf: PdfInfo }>(
    `/pdf/${id}/replace-text`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    },
  )

export const rotatePage = (id: string, page: number) =>
  request<PdfInfo>(`/pdf/${id}/rotate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pages: [page], angle: 90 }),
  })

export const compressPdf = (id: string, level: 'quality' | 'balanced' | 'small' = 'balanced') =>
  request<{ original_size: number; output_size: number; ratio: number; note: string }>(`/pdf/${id}/compress`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ level }),
  })

type LocalJob<T = Record<string, unknown>> = { id: string; status: 'queued' | 'running' | 'cancelling' | 'cancelled' | 'completed' | 'failed'; progress: number; result: T | null; error: string | null }

export async function compressPdfQueued(id: string, level: 'quality' | 'balanced' | 'small', onUpdate?: (job: LocalJob) => void) {
  let job = await request<LocalJob>(`/jobs/pdf/${id}/compress`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ level }) })
  onUpdate?.(job)
  while (!['completed', 'failed', 'cancelled'].includes(job.status)) {
    await new Promise((resolve) => setTimeout(resolve, 180))
    job = await request<LocalJob>(`/jobs/${job.id}`); onUpdate?.(job)
  }
  if (job.status === 'failed') throw new Error(job.error || 'Arka plan işi başarısız oldu')
  if (job.status === 'cancelled') throw new Error('İşlem iptal edildi')
  return job.result as { original_size: number; output_size: number; ratio: number; note: string }
}

export const cancelLocalJob = (jobId: string) => request<LocalJob>(`/jobs/${jobId}/cancel`, { method: 'POST' })

export const deletePdfPages = (id: string, pages: number[]) =>
  request<PdfInfo>(`/pdf/${id}/pages/delete`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pages }),
  })

export const reorderPdfPages = (id: string, order: number[]) =>
  request<PdfInfo>(`/pdf/${id}/pages/reorder`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ order }),
  })

export const cropPdfPage = (id: string, page: number, rect: number[]) =>
  request<PdfInfo>(`/pdf/${id}/pages/crop`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ page, rect }),
  })

export const addBlankPdfPage = (id: string, afterPage: number) =>
  request<PdfInfo>(`/pdf/${id}/pages/blank`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ after_page: afterPage }),
  })

export const decoratePdfPages = (id: string, payload: unknown) =>
  request<PdfInfo>(`/pdf/${id}/pages/decorate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  })

export const addPdfText = (id: string, payload: unknown) =>
  request<PdfInfo>(`/pdf/${id}/content/text`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  })

export const addPdfShape = (id: string, payload: unknown) =>
  request<PdfInfo>(`/pdf/${id}/content/shape`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  })

export const addPdfInk = (id: string, payload: unknown) =>
  request<PdfInfo>(`/pdf/${id}/content/ink`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  })

export const ocrPdf = (id: string, language = 'tur+eng', force = false) =>
  request<{ pdf: PdfInfo; audit: { language: string; missing_languages: string[]; word_count: number; average_confidence: number; pages_processed: number; pages_skipped: number } }>(`/pdf/${id}/ocr`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ language, dpi: 200, force }),
  })

export const addPdfWatermark = (id: string, payload: unknown) =>
  request<PdfInfo>(`/pdf/${id}/content/watermark`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })

export const removePdfWatermarks = (id: string) =>
  request<PdfInfo>(`/pdf/${id}/content/watermark/remove`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })

export const addPdfLink = (id: string, payload: unknown) =>
  request<PdfInfo>(`/pdf/${id}/content/link`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })

export const redactPdfAreas = (id: string, payload: unknown) =>
  request<{ pdf: PdfInfo; audit: { areas: number; removed_characters: number } }>(`/pdf/${id}/content/redact`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  })

export const undoPdf = (id: string) =>
  request<PdfInfo>(`/pdf/${id}/undo`, { method: 'POST' })

export const redoPdf = (id: string) =>
  request<PdfInfo>(`/pdf/${id}/redo`, { method: 'POST' })

export async function addPdfImage(id: string, file: File, page: number, rect: number[]): Promise<PdfInfo> {
  const form = new FormData()
  form.append('file', file)
  form.append('page', String(page))
  form.append('rect', JSON.stringify(rect))
  const response = await apiFetch(`/pdf/${id}/content/image`, { method: 'POST', body: form })
  if (!response.ok) throw new Error(await errorMessage(response))
  const body = await response.json()
  return body.data as PdfInfo
}

export async function encryptPdf(id: string, payload: unknown): Promise<Blob> {
  const response = await apiFetch(`/pdf/${id}/security/encrypt`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  })
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.blob()
}

export const unlockPdf = (id: string, password: string) =>
  request<PdfInfo>(`/pdf/${id}/security/unlock`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password }),
  })

export const updatePdfMetadata = (id: string, payload: unknown) =>
  request<PdfInfo>(`/pdf/${id}/metadata`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  })

export async function splitPdf(id: string, ranges: string[]): Promise<Blob> {
  const response = await apiFetch(`/pdf/${id}/split`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ranges }),
  })
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.blob()
}

export async function mergePdfs(files: File[]): Promise<Blob> {
  const form = new FormData()
  files.forEach((file) => form.append('files', file))
  const response = await apiFetch('/pdf/merge', { method: 'POST', body: form })
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.blob()
}

export async function downloadDocument(id: string): Promise<Blob> {
  const response = await apiFetch(`/files/${id}/download`)
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.blob()
}

export const getDocumentHistory = (id: string) =>
  request<{ operation: string; timestamp: number; details: Record<string, unknown> }[]>(`/files/${id}/history`)

export async function convertImage(id: string, options: Record<string, string>): Promise<Blob> {
  const form = new FormData()
  Object.entries(options).forEach(([key, value]) => form.append(key, value))
  const response = await apiFetch(`/images/${id}/convert`, { method: 'POST', body: form })
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.blob()
}

export async function editImage(id: string, options: Record<string, string>): Promise<Blob> {
  const form = new FormData()
  Object.entries(options).forEach(([key, value]) => form.append(key, value))
  const response = await apiFetch(`/images/${id}/edit`, { method: 'POST', body: form })
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.blob()
}

export async function compressImage(id: string, options: Record<string, string>): Promise<Blob> {
  const form = new FormData()
  Object.entries(options).forEach(([key, value]) => form.append(key, value))
  const response = await apiFetch(`/images/${id}/compress`, { method: 'POST', body: form })
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.blob()
}

export async function convertPdfToDocx(id: string): Promise<Blob> {
  const response = await apiFetch(`/convert/pdf/${id}/docx`)
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.blob()
}

export async function convertPdfToXlsx(id: string): Promise<Blob> {
  const response = await apiFetch(`/convert/pdf/${id}/xlsx`)
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.blob()
}

export async function convertPdfToPptx(id: string): Promise<Blob> {
  const response = await apiFetch(`/convert/pdf/${id}/pptx`)
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.blob()
}

export const inspectOffice = (id: string) => request<Record<string, unknown>>(`/office/${id}`)

export const saveOffice = (id: string, updates: Record<string, unknown>[]) =>
  request<Record<string, unknown>>(`/office/${id}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ updates }),
  })

export async function convertOfficeToPdf(id: string): Promise<Blob> {
  const response = await apiFetch(`/convert/office/${id}/pdf`)
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.blob()
}

export async function convertPdfToImages(id: string, format: 'png' | 'jpg' = 'png'): Promise<Blob> {
  const response = await apiFetch(`/convert/pdf/${id}/images?output_format=${format}&dpi=144&quality=88`)
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.blob()
}

export async function convertDocxToPdf(id: string): Promise<Blob> {
  const response = await apiFetch(`/convert/docx/${id}/pdf`)
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.blob()
}

export async function convertImagesToPdf(files: File[]): Promise<Blob> {
  const form = new FormData()
  files.forEach((file) => form.append('files', file))
  const response = await apiFetch('/convert/images/pdf', { method: 'POST', body: form })
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.blob()
}

export async function convertScansToSearchablePdf(files: File[], language = 'tur+eng'): Promise<Blob> {
  const form = new FormData()
  files.forEach((file) => form.append('files', file))
  form.append('language', language)
  form.append('dpi', '200')
  const response = await apiFetch('/ocr/images/pdf', { method: 'POST', body: form })
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.blob()
}

export async function batchConvertImages(files: File[], outputFormat = 'WEBP', quality = 82): Promise<Blob> {
  const form = new FormData(); files.forEach((file) => form.append('files', file))
  form.append('output_format', outputFormat); form.append('quality', String(quality))
  const response = await apiFetch('/batch/images/convert', { method: 'POST', body: form })
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.blob()
}

export async function batchCompressPdfs(files: File[], level = 'balanced'): Promise<Blob> {
  const form = new FormData(); files.forEach((file) => form.append('files', file)); form.append('level', level)
  const response = await apiFetch('/batch/pdf/compress', { method: 'POST', body: form })
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.blob()
}

export async function saveBlob(blob: Blob, defaultPath: string): Promise<void> {
  if (window.desktop) {
    const extension = defaultPath.split('.').pop() || '*'
    const result = await window.desktop.saveDialog({
      defaultPath,
      filters: [{ name: 'Dosya', extensions: [extension] }],
    })
    if (!result.canceled && result.filePath) {
      await window.desktop.writeFile(result.filePath, await blob.arrayBuffer())
      await window.desktop.showItemInFolder(result.filePath)
    }
    return
  }
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = defaultPath
  anchor.click()
  URL.revokeObjectURL(url)
}
