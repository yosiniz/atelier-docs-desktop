export type PdfPage = {
  index: number
  number: number
  width: number
  height: number
  rotation: number
  word_count: number
}

export type PdfInfo = {
  page_count: number
  pages: PdfPage[]
  metadata: Record<string, string>
  encrypted: boolean
  scanned_likely: boolean
}

export type UploadedDocument = {
  id: string
  name: string
  size: number
  kind: 'pdf' | 'image' | 'office'
  pdf?: PdfInfo
  image?: { width: number; height: number; format: string }
}

export type TextBlock = {
  id: string
  text: string
  bbox: [number, number, number, number]
  baseline: number
  font: string
  font_size: number
  color: string
  bold: boolean
  italic: boolean
}
