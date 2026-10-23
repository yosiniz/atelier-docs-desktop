import { type ChangeEvent, type PointerEvent as ReactPointerEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowDown, ArrowLeft, ArrowUp, ChevronLeft, ChevronRight, ClipboardPaste, Copy, Crop, Download, FileCog, FileSpreadsheet, FileText, ListOrdered, LoaderCircle, Presentation,
  FileDown, Images, LockKeyhole, Maximize2, Minus, PanelLeftClose, Plus, RotateCw, Save, Scissors, Search, Settings2,
  History, ImagePlus, Link2, MousePointer2, PenLine, Redo2, ShieldX, Shrink, Signature, Stamp, Square, Trash2, Type, Undo2, UnlockKeyhole, X,
} from 'lucide-react'
import { Brand } from '../components/Brand'
import { Toast } from '../components/Toast'
import { SignaturePad } from '../components/SignaturePad'
import { addBlankPdfPage, addPdfImage, addPdfInk, addPdfLink, addPdfShape, addPdfText, addPdfWatermark, cancelLocalJob, compressPdfQueued, convertPdfToDocx, convertPdfToImages, convertPdfToPptx, convertPdfToXlsx, cropPdfPage, decoratePdfPages, deletePdfPages, downloadDocument, editText, encryptPdf, getDocumentHistory, getPdfImages, getTextBlocks, movePdfImage, ocrPdf, redactPdfAreas, redoPdf, removePdfWatermarks, renderUrl, reorderPdfPages, replacePdfText, rotatePage, saveBlob, searchPdfText, splitPdf, undoPdf, unlockPdf, updatePdfMetadata, type PdfImageElement } from '../lib/api'
import { translateRectWithinPage, type Rect } from '../lib/geometry'
import { useAppStore } from '../store'
import type { TextBlock } from '../types'

type TextAlignment = 'left' | 'center' | 'right' | 'justify'
type TextStyleClipboard = {
  fontSize: number
  fontFamily: string
  color: string
  align: TextAlignment
  bold: boolean
  italic: boolean
  underline: boolean
}

export function PdfEditorPage() {
  const navigate = useNavigate()
  const imageInput = useRef<HTMLInputElement>(null)
  const document = useAppStore((state) => state.document)
  const [page, setPage] = useState(0)
  const [zoom, setZoom] = useState(0.9)
  const [blocks, setBlocks] = useState<TextBlock[]>([])
  const [pageImages, setPageImages] = useState<PdfImageElement[]>([])
  const [selected, setSelected] = useState<TextBlock | null>(null)
  const [selectedImage, setSelectedImage] = useState<PdfImageElement | null>(null)
  const [text, setText] = useState('')
  const [fontSize, setFontSize] = useState(11)
  const [color, setColor] = useState('#111827')
  const [fontFamily, setFontFamily] = useState('Arial')
  const [bold, setBold] = useState(false)
  const [italic, setItalic] = useState(false)
  const [underline, setUnderline] = useState(false)
  const [align, setAlign] = useState<TextAlignment>('left')
  const [copiedTextStyle, setCopiedTextStyle] = useState<TextStyleClipboard | null>(null)
  const [editRect, setEditRect] = useState<[number, number, number, number] | null>(null)
  const [cacheKey, setCacheKey] = useState(0)
  const [busy, setBusy] = useState(false)
  const [activeJob, setActiveJob] = useState<{ id: string; progress: number } | null>(null)
  const [splitSpec, setSplitSpec] = useState('1')
  const [toast, setToast] = useState<{ message: string; kind: 'success' | 'error' } | null>(null)
  const [mode, setMode] = useState<'edit' | 'addText' | 'addImage' | 'shape' | 'redact' | 'crop' | 'draw' | 'link'>('edit')
  const [draftRect, setDraftRect] = useState<[number, number, number, number] | null>(null)
  const [dragStart, setDragStart] = useState<[number, number] | null>(null)
  const [shapeKind, setShapeKind] = useState<'rectangle' | 'ellipse' | 'line'>('rectangle')
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [unlockPassword, setUnlockPassword] = useState('')
  const [protectPassword, setProtectPassword] = useState('')
  const [protectOpen, setProtectOpen] = useState(false)
  const [metadataOpen, setMetadataOpen] = useState(false)
  const [compressionOpen, setCompressionOpen] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [pageDecorOpen, setPageDecorOpen] = useState(false)
  const [headerText, setHeaderText] = useState('')
  const [footerText, setFooterText] = useState('')
  const [pageNumbers, setPageNumbers] = useState(true)
  const [startNumber, setStartNumber] = useState(1)
  const [draggedPage, setDraggedPage] = useState<number | null>(null)
  const [signatureOpen, setSignatureOpen] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [watermarkOpen, setWatermarkOpen] = useState(false)
  const [watermarkText, setWatermarkText] = useState('GİZLİ')
  const [linkUrl, setLinkUrl] = useState('https://')
  const [historyItems, setHistoryItems] = useState<{ operation: string; timestamp: number; details: Record<string, unknown> }[]>([])
  const inkPathRef = useRef<[number, number][]>([])
  const textDragRef = useRef<{
    pointerId: number
    block: TextBlock
    start: [number, number]
    origin: Rect
    target: Rect
    moved: boolean
    value: string
    style: { font_size: number; font_family: string; color: string; align: typeof align; bold: boolean; italic: boolean; underline: boolean }
  } | null>(null)
  const suppressTextClickRef = useRef(false)
  const imageDragRef = useRef<{ pointerId: number; image: PdfImageElement; start: [number, number]; origin: Rect; target: Rect; moved: boolean } | null>(null)
  const suppressImageClickRef = useRef(false)
  const pageElementRef = useRef<HTMLDivElement>(null)
  const [draggingTextId, setDraggingTextId] = useState<string | null>(null)
  const [draggingImageId, setDraggingImageId] = useState<string | null>(null)
  const [inkPath, setInkPath] = useState<[number, number][]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [replacement, setReplacement] = useState('')
  const [caseSensitive, setCaseSensitive] = useState(false)
  const [wholeWord, setWholeWord] = useState(false)
  const [matchCount, setMatchCount] = useState<number | null>(null)
  const [compressionLevel, setCompressionLevel] = useState<'quality' | 'balanced' | 'small'>('balanced')
  const [metadata, setMetadata] = useState({ title: '', author: '', subject: '', keywords: '' })
  const pdf = document?.pdf
  const pageInfo = pdf?.pages[page]

  const loadBlocks = useCallback(async () => {
    if (!document || document.pdf?.encrypted) return
    try { setBlocks(await getTextBlocks(document.id, page)) }
    catch (error) { setToast({ message: error instanceof Error ? error.message : 'Metin katmanı okunamadı', kind: 'error' }) }
  }, [document, page])

  const loadImages = useCallback(async () => {
    if (!document || document.pdf?.encrypted) return
    try { setPageImages(await getPdfImages(document.id, page)) }
    catch (error) { setToast({ message: error instanceof Error ? error.message : 'Görsel nesneleri okunamadı', kind: 'error' }) }
  }, [document, page])

  useEffect(() => { void loadBlocks(); void loadImages(); setSelected(null); setSelectedImage(null) }, [loadBlocks, loadImages, cacheKey])
  useEffect(() => { if (!document || document.kind !== 'pdf') navigate('/') }, [document, navigate])

  const selectBlock = (block: TextBlock) => {
    if (mode !== 'edit') return
    setSelectedImage(null)
    setSelected(block); setText(block.text); setFontSize(Math.round(block.font_size * 100) / 100); setColor(block.color)
    setBold(block.bold); setItalic(block.italic); setUnderline(false); setAlign('left'); setFontFamily(block.font || 'Arial'); setEditRect([...block.bbox])
  }

  const chooseMode = (nextMode: typeof mode) => {
    setMode(nextMode); setSelected(null); setSelectedImage(null); setEditRect(null); setDraftRect(null); setDragStart(null)
    if (nextMode === 'addText') setText('Yeni metin')
  }

  const chooseImage = () => {
    chooseMode('addImage')
    requestAnimationFrame(() => imageInput.current?.click())
  }

  const receiveImage = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null
    event.target.value = ''
    setImageFile(file)
    if (!file) chooseMode('edit')
  }

  const run = async (job: () => Promise<void>) => {
    setBusy(true)
    try { await job() } catch (error) {
      setToast({ message: error instanceof Error ? error.message : 'İşlem başarısız', kind: 'error' })
    } finally { setBusy(false); setActiveJob(null) }
  }

  const copyTextStyle = () => {
    if (!selected) return
    setCopiedTextStyle({ fontSize, fontFamily, color, align, bold, italic, underline })
    setToast({ message: 'Metin biçimi kopyalandı. Başka bir metne veya yeni metne yapıştırabilirsiniz.', kind: 'success' })
  }

  const pasteTextStyle = () => {
    if (!copiedTextStyle) return
    setFontSize(copiedTextStyle.fontSize)
    setFontFamily(copiedTextStyle.fontFamily)
    setColor(copiedTextStyle.color)
    setAlign(copiedTextStyle.align)
    setBold(copiedTextStyle.bold)
    setItalic(copiedTextStyle.italic)
    setUnderline(copiedTextStyle.underline)
    setToast({ message: 'Kopyalanan renk, punto, yazı tipi ve karakter biçimi uygulandı.', kind: 'success' })
  }

  const applyEdit = () => selected && document && run(async () => {
    const result = await editText(document.id, {
      page, rect: selected.bbox, target_rect: editRect || selected.bbox, source_baseline: selected.baseline, text, original_text: selected.text,
      style: { font_size: fontSize, font_family: fontFamily, color, align, bold, italic, underline },
    })
    document.pdf = result.pdf
    setCacheKey((value) => value + 1)
    setSelected(null); setEditRect(null)
    setToast({ message: 'Metin içerik akışından kaldırılıp yeniden yazıldı.', kind: 'success' })
  })

  const download = () => document && run(async () => saveBlob(await downloadDocument(document.id), `${document.name.replace(/\.pdf$/i, '')}-duzenlendi.pdf`))
  const exportWord = () => document && run(async () => {
    await saveBlob(await convertPdfToDocx(document.id), `${document.name.replace(/\.pdf$/i, '')}.docx`)
    setToast({ message: 'Düzenlenebilir Word belgesi hazırlandı.', kind: 'success' })
  })
  const exportImages = () => document && run(async () => {
    await saveBlob(await convertPdfToImages(document.id, 'png'), `${document.name.replace(/\.pdf$/i, '')}-sayfalar.zip`)
    setToast({ message: 'PDF sayfaları PNG olarak hazırlandı.', kind: 'success' })
  })
  const exportExcel = () => document && run(async () => {
    await saveBlob(await convertPdfToXlsx(document.id), `${document.name.replace(/\.pdf$/i, '')}.xlsx`)
    setToast({ message: 'Düzenlenebilir Excel dosyası hazırlandı.', kind: 'success' })
  })
  const exportPowerPoint = () => document && run(async () => {
    await saveBlob(await convertPdfToPptx(document.id), `${document.name.replace(/\.pdf$/i, '')}.pptx`)
    setToast({ message: 'Düzenlenebilir PowerPoint dosyası hazırlandı.', kind: 'success' })
  })
  const protect = () => document && run(async () => {
    const blob = await encryptPdf(document.id, {
      user_password: protectPassword, owner_password: protectPassword,
      allow_print: true, allow_copy: false, allow_annotate: false,
    })
    await saveBlob(blob, `${document.name.replace(/\.pdf$/i, '')}-sifreli.pdf`)
    setProtectOpen(false); setProtectPassword('')
    setToast({ message: 'AES-256 şifreli PDF kopyası kaydedildi.', kind: 'success' })
  })
  const unlock = () => document && run(async () => {
    document.pdf = await unlockPdf(document.id, unlockPassword)
    setUnlockPassword(''); setCacheKey((value) => value + 1)
    setToast({ message: 'PDF kilidi geçerli parolayla açıldı.', kind: 'success' })
  })
  const openMetadata = () => {
    const source = pdf?.metadata || {}
    setMetadata({ title: source.title || '', author: source.author || '', subject: source.subject || '', keywords: source.keywords || '' })
    setMetadataOpen(true)
  }
  const saveMetadata = () => document && run(async () => {
    document.pdf = await updatePdfMetadata(document.id, metadata)
    setMetadataOpen(false); setCacheKey((value) => value + 1)
    setToast({ message: 'PDF dosya bilgileri güncellendi.', kind: 'success' })
  })
  const rotate = () => document && run(async () => {
    document.pdf = await rotatePage(document.id, page); setCacheKey((value) => value + 1)
    setToast({ message: 'Sayfa 90° döndürüldü.', kind: 'success' })
  })
  const undo = () => document && run(async () => {
    document.pdf = await undoPdf(document.id); setPage((value) => Math.min(value, document.pdf!.page_count - 1)); setCacheKey((value) => value + 1)
    setToast({ message: 'Son işlem geri alındı.', kind: 'success' })
  })
  const redo = () => document && run(async () => {
    document.pdf = await redoPdf(document.id); setPage((value) => Math.min(value, document.pdf!.page_count - 1)); setCacheKey((value) => value + 1)
    setToast({ message: 'İşlem yeniden uygulandı.', kind: 'success' })
  })
  const compress = () => document && run(async () => {
    const result = await compressPdfQueued(document.id, compressionLevel, (job) => setActiveJob({ id: job.id, progress: job.progress })); setCacheKey((value) => value + 1)
    setActiveJob(null)
    setCompressionOpen(false)
    setToast({ message: result.ratio > 0 ? `Dosya boyutu %${result.ratio} azaltıldı.` : 'Dosya zaten optimize edilmiş.', kind: 'success' })
  })
  const findText = () => document && searchQuery.trim() && run(async () => {
    const result = await searchPdfText(document.id, searchQuery.trim(), caseSensitive, wholeWord)
    setMatchCount(result.count)
    if (result.matches[0]) setPage(result.matches[0].page)
    setToast({ message: result.count ? `${result.count} eşleşme bulundu.` : 'Aranan metin bulunamadı.', kind: result.count ? 'success' : 'error' })
  })
  const replaceAll = () => document && searchQuery.trim() && run(async () => {
    const result = await replacePdfText(document.id, {
      query: searchQuery.trim(), replacement, case_sensitive: caseSensitive, whole_word: wholeWord,
    })
    document.pdf = result.pdf
    setMatchCount(0); setSearchOpen(false); setCacheKey((value) => value + 1)
    setToast({ message: `${result.audit.matches} eşleşme kalıcı olarak değiştirildi.`, kind: 'success' })
  })
  const addBlankPage = () => document && run(async () => {
    document.pdf = await addBlankPdfPage(document.id, page); setPage(page + 1); setCacheKey((value) => value + 1)
    setToast({ message: 'Boş sayfa eklendi.', kind: 'success' })
  })
  const applyPageDecor = () => document && run(async () => {
    document.pdf = await decoratePdfPages(document.id, { header: headerText, footer: footerText, page_numbers: pageNumbers, start_number: startNumber })
    setPageDecorOpen(false); setCacheKey((value) => value + 1)
    setToast({ message: 'Sayfa bilgileri uygulandı.', kind: 'success' })
  })
  const openHistory = () => document && run(async () => { setHistoryItems((await getDocumentHistory(document.id)).reverse()); setHistoryOpen(true) })
  const applyOcr = () => document && run(async () => {
    const result = await ocrPdf(document.id); document.pdf = result.pdf; setCacheKey((value) => value + 1)
    setToast({ message: `OCR tamamlandı: ${result.audit.word_count} sözcük, ortalama güven %${result.audit.average_confidence}.`, kind: 'success' })
  })
  const applyWatermark = () => document && run(async () => { document.pdf = await addPdfWatermark(document.id, { text: watermarkText, font_size: 42, color: '#9ca3af', opacity: .25, rotation: 0 }); setWatermarkOpen(false); setCacheKey((value) => value + 1); setToast({ message: 'Kaldırılabilir filigran eklendi.', kind: 'success' }) })
  const removeWatermark = () => document && run(async () => { document.pdf = await removePdfWatermarks(document.id); setWatermarkOpen(false); setCacheKey((value) => value + 1); setToast({ message: 'Atelier filigranları kaldırıldı.', kind: 'success' }) })
  const split = () => document && run(async () => {
    const ranges = splitSpec.split(';').map((value) => value.trim()).filter(Boolean)
    await saveBlob(await splitPdf(document.id, ranges), 'atelier-bolunmus.zip')
    setToast({ message: 'Seçilen sayfalar ZIP olarak hazırlandı.', kind: 'success' })
  })

  const removePage = (index: number) => document && run(async () => {
    document.pdf = await deletePdfPages(document.id, [index])
    setPage(Math.min(page, document.pdf.page_count - 1))
    setCacheKey((value) => value + 1)
    setToast({ message: `${index + 1}. sayfa kalıcı olarak silindi.`, kind: 'success' })
  })

  const movePage = (index: number, direction: -1 | 1) => {
    const currentPdf = document?.pdf
    if (!document || !currentPdf) return
    return run(async () => {
    const target = index + direction
    if (target < 0 || target >= currentPdf.page_count) return
    const order = currentPdf.pages.map((item) => item.index)
    ;[order[index], order[target]] = [order[target], order[index]]
    document.pdf = await reorderPdfPages(document.id, order)
    setPage(target)
    setCacheKey((value) => value + 1)
    setToast({ message: 'Sayfa sırası güncellendi.', kind: 'success' })
    })
  }
  const dropPage = (target: number) => {
    const currentPdf = document?.pdf; const source = draggedPage; setDraggedPage(null)
    if (!document || !currentPdf || source === null || source === target) return
    void run(async () => {
      const order = currentPdf.pages.map((item) => item.index)
      const [moved] = order.splice(source, 1); order.splice(target, 0, moved)
      document.pdf = await reorderPdfPages(document.id, order); setPage(target); setCacheKey((value) => value + 1)
      setToast({ message: 'Sayfa sürüklenerek yeniden sıralandı.', kind: 'success' })
    })
  }

  const pointOnPage = (event: ReactPointerEvent<HTMLDivElement>): [number, number] => {
    const bounds = pageElementRef.current?.getBoundingClientRect() || event.currentTarget.getBoundingClientRect()
    return [
      Math.max(0, Math.min(pageInfo?.width || 0, (event.clientX - bounds.left) / zoom)),
      Math.max(0, Math.min(pageInfo?.height || 0, (event.clientY - bounds.top) / zoom)),
    ]
  }

  const pointFromClient = (clientX: number, clientY: number): [number, number] => {
    const bounds = pageElementRef.current?.getBoundingClientRect()
    if (!bounds) return [0, 0]
    return [
      Math.max(0, Math.min(pageInfo?.width || 0, (clientX - bounds.left) / zoom)),
      Math.max(0, Math.min(pageInfo?.height || 0, (clientY - bounds.top) / zoom)),
    ]
  }

  const startTextDrag = (event: ReactPointerEvent<HTMLButtonElement>, block: TextBlock) => {
    if (mode !== 'edit' || busy || event.button !== 0) return
    event.stopPropagation()
    event.currentTarget.setPointerCapture(event.pointerId)
    const isCurrent = selected?.id === block.id
    const origin = [...(isCurrent && editRect ? editRect : block.bbox)] as Rect
    if (!isCurrent) selectBlock(block)
    textDragRef.current = {
      pointerId: event.pointerId,
      block,
      start: pointFromClient(event.clientX, event.clientY),
      origin,
      target: origin,
      moved: false,
      value: isCurrent ? text : block.text,
      style: {
        font_size: isCurrent ? fontSize : Math.round(block.font_size * 100) / 100,
        font_family: isCurrent ? fontFamily : block.font || 'Arial',
        color: isCurrent ? color : block.color,
        align: isCurrent ? align : 'left',
        bold: isCurrent ? bold : block.bold,
        italic: isCurrent ? italic : block.italic,
        underline: isCurrent ? underline : false,
      },
    }
    setDraggingTextId(block.id)
  }

  const updateTextDrag = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const drag = textDragRef.current
    if (!drag || drag.pointerId !== event.pointerId || !pageInfo) return
    event.stopPropagation()
    const point = pointFromClient(event.clientX, event.clientY)
    const deltaX = point[0] - drag.start[0]
    const deltaY = point[1] - drag.start[1]
    if (!drag.moved && Math.hypot(deltaX * zoom, deltaY * zoom) < 3) return
    drag.moved = true
    drag.target = translateRectWithinPage(drag.origin, deltaX, deltaY, pageInfo.width, pageInfo.height)
    setEditRect(drag.target)
  }

  const finishTextDrag = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const drag = textDragRef.current
    if (!drag || drag.pointerId !== event.pointerId) return
    event.stopPropagation()
    textDragRef.current = null
    setDraggingTextId(null)
    if (!drag.moved || !document) return
    suppressTextClickRef.current = true
    void run(async () => {
      const result = await editText(document.id, {
        page,
        rect: drag.block.bbox,
        target_rect: drag.target,
        source_baseline: drag.block.baseline,
        text: drag.value,
        original_text: drag.block.text,
        style: drag.style,
      })
      document.pdf = result.pdf
      setSelected(null); setEditRect(null); setCacheKey((value) => value + 1)
      setToast({ message: 'Metin kutusu yeni konumuna taşındı.', kind: 'success' })
    })
  }

  const cancelTextDrag = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const drag = textDragRef.current
    if (!drag || drag.pointerId !== event.pointerId) return
    textDragRef.current = null
    setDraggingTextId(null)
    setEditRect(drag.origin)
  }

  const clickTextBlock = (block: TextBlock) => {
    if (suppressTextClickRef.current) { suppressTextClickRef.current = false; return }
    selectBlock(block)
  }

  const selectImageElement = (image: PdfImageElement) => {
    if (mode !== 'edit') return
    setSelected(null); setSelectedImage(image); setEditRect([...image.bbox])
  }

  const startImageDrag = (event: ReactPointerEvent<HTMLButtonElement>, image: PdfImageElement) => {
    if (mode !== 'edit' || busy || event.button !== 0) return
    event.stopPropagation()
    event.currentTarget.setPointerCapture(event.pointerId)
    const origin = [...(selectedImage?.id === image.id && editRect ? editRect : image.bbox)] as Rect
    if (selectedImage?.id !== image.id) selectImageElement(image)
    imageDragRef.current = {
      pointerId: event.pointerId, image, start: pointFromClient(event.clientX, event.clientY), origin, target: origin, moved: false,
    }
    setDraggingImageId(image.id)
  }

  const updateImageDrag = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const drag = imageDragRef.current
    if (!drag || drag.pointerId !== event.pointerId || !pageInfo) return
    event.stopPropagation()
    const point = pointFromClient(event.clientX, event.clientY)
    const deltaX = point[0] - drag.start[0]
    const deltaY = point[1] - drag.start[1]
    if (!drag.moved && Math.hypot(deltaX * zoom, deltaY * zoom) < 3) return
    drag.moved = true
    drag.target = translateRectWithinPage(drag.origin, deltaX, deltaY, pageInfo.width, pageInfo.height)
    setEditRect(drag.target)
  }

  const finishImageDrag = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const drag = imageDragRef.current
    if (!drag || drag.pointerId !== event.pointerId) return
    event.stopPropagation()
    imageDragRef.current = null; setDraggingImageId(null)
    if (!drag.moved || !document) return
    suppressImageClickRef.current = true
    void run(async () => {
      document.pdf = await movePdfImage(document.id, {
        page, xref: drag.image.xref, source_rect: drag.image.bbox, target_rect: drag.target,
      })
      setSelectedImage(null); setEditRect(null); setCacheKey((value) => value + 1)
      setToast({ message: 'Görsel yeni konumuna taşındı.', kind: 'success' })
    })
  }

  const cancelImageDrag = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const drag = imageDragRef.current
    if (!drag || drag.pointerId !== event.pointerId) return
    imageDragRef.current = null; setDraggingImageId(null); setEditRect(drag.origin)
  }

  const clickImageElement = (image: PdfImageElement) => {
    if (suppressImageClickRef.current) { suppressImageClickRef.current = false; return }
    selectImageElement(image)
  }

  const startArea = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (mode === 'edit') return
    event.currentTarget.setPointerCapture(event.pointerId)
    const point = pointOnPage(event)
    if (mode === 'draw') { inkPathRef.current = [point]; setInkPath([point]); return }
    setDragStart(point)
    setDraftRect([point[0], point[1], point[0], point[1]])
  }

  const updateArea = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (mode === 'draw' && inkPathRef.current.length) { const next = [...inkPathRef.current, pointOnPage(event)]; inkPathRef.current = next; setInkPath(next); return }
    if (mode === 'edit' || !dragStart) return
    const point = pointOnPage(event)
    setDraftRect([Math.min(dragStart[0], point[0]), Math.min(dragStart[1], point[1]), Math.max(dragStart[0], point[0]), Math.max(dragStart[1], point[1])])
  }

  const finishArea = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (mode === 'draw' && inkPathRef.current.length) {
      const path = [...inkPathRef.current, pointOnPage(event)]; inkPathRef.current = []; setInkPath([])
      if (document && path.length > 1) void run(async () => { document.pdf = await addPdfInk(document.id, { page, paths: [path], color, width: 2 }); setCacheKey((value) => value + 1); setToast({ message: 'Serbest çizim PDF içeriğine eklendi.', kind: 'success' }) })
      return
    }
    if (mode === 'edit' || !dragStart) return
    const point = pointOnPage(event)
    let x0 = Math.min(dragStart[0], point[0]); let y0 = Math.min(dragStart[1], point[1])
    let x1 = Math.max(dragStart[0], point[0]); let y1 = Math.max(dragStart[1], point[1])
    if (x1 - x0 < 12) x1 = Math.min(pageInfo?.width || x0 + 180, x0 + 180)
    if (y1 - y0 < 12) y1 = Math.min(pageInfo?.height || y0 + 54, y0 + 54)
    setDraftRect([x0, y0, x1, y1]); setDragStart(null)
  }

  const applyCanvasAction = () => document && draftRect && run(async () => {
    if (mode === 'addText') {
      document.pdf = await addPdfText(document.id, { page, rect: draftRect, text, style: { font_size: fontSize, font_family: fontFamily, color, align, bold, italic, underline } })
      setToast({ message: 'Yeni metin PDF içeriğine eklendi.', kind: 'success' })
    } else if (mode === 'addImage' && imageFile) {
      document.pdf = await addPdfImage(document.id, imageFile, page, draftRect)
      setToast({ message: 'Görsel PDF sayfasına gömüldü.', kind: 'success' })
    } else if (mode === 'shape') {
      document.pdf = await addPdfShape(document.id, { page, rect: draftRect, kind: shapeKind, stroke_color: color, fill_color: null, width: 2 })
      setToast({ message: 'Şekil PDF sayfasına eklendi.', kind: 'success' })
    } else if (mode === 'redact') {
      const result = await redactPdfAreas(document.id, { page, rects: [draftRect] })
      document.pdf = result.pdf
      setToast({ message: `Alan kalıcı olarak redakte edildi (${result.audit.removed_characters} karakter kaldırıldı).`, kind: 'success' })
    } else if (mode === 'crop') {
      document.pdf = await cropPdfPage(document.id, page, draftRect)
      setToast({ message: 'Sayfa kırpıldı.', kind: 'success' })
    } else if (mode === 'link') {
      document.pdf = await addPdfLink(document.id, { page, rect: draftRect, uri: linkUrl })
      setToast({ message: 'Tıklanabilir bağlantı eklendi.', kind: 'success' })
    }
    setDraftRect(null); setCacheKey((value) => value + 1)
  })

  const viewport = useMemo(() => pageInfo ? { width: pageInfo.width * zoom, height: pageInfo.height * zoom } : { width: 0, height: 0 }, [pageInfo, zoom])
  const updateEditRect = (field: 'x' | 'y' | 'width' | 'height', rawValue: number) => {
    if (!editRect || !Number.isFinite(rawValue)) return
    const [x0, y0, x1, y1] = editRect
    if (field === 'x') setEditRect([rawValue, y0, rawValue + (x1 - x0), y1])
    else if (field === 'y') setEditRect([x0, rawValue, x1, rawValue + (y1 - y0)])
    else if (field === 'width') setEditRect([x0, y0, x0 + Math.max(8, rawValue), y1])
    else setEditRect([x0, y0, x1, y0 + Math.max(8, rawValue)])
  }
  if (!document || !pdf) return null
  if (pdf.encrypted) return <main className="unlock-shell">
    <header className="editor-header"><button className="icon-button" onClick={() => navigate('/')} aria-label="Ana sayfa"><ArrowLeft size={19} /></button><Brand /></header>
    <section className="unlock-card"><span className="unlock-icon"><LockKeyhole size={30} /></span><h1>Bu PDF parola korumalı</h1><p>Belgeyi yerel olarak açmak için geçerli kullanıcı veya sahip parolasını girin. Parola cihazınızdan gönderilmez.</p><label>PDF parolası<input type="password" value={unlockPassword} onChange={(event) => setUnlockPassword(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && unlock()} /></label><button className="primary-button full" disabled={busy || !unlockPassword} onClick={unlock}>{busy ? <LoaderCircle className="spin" size={17} /> : <UnlockKeyhole size={17} />} Kilidi aç</button></section>
    {toast && <Toast {...toast} onClose={() => setToast(null)} />}
  </main>
  if (!pageInfo) return null

  return <main className="editor-shell">
    <header className="editor-header">
      <button className="icon-button" onClick={() => navigate('/')} aria-label="Ana sayfa"><ArrowLeft size={19} /></button>
      <Brand /><span className="header-divider" />
      <div className="document-name"><FileText size={17} /><div><strong>{document.name}</strong><small>{pdf.page_count} sayfa · {(document.size / 1024 / 1024).toFixed(1)} MB</small></div></div>
      <div className="editor-actions">
        <button className="secondary-button" onClick={openMetadata} disabled={busy}><FileCog size={16} /> Bilgi</button>
        <button className="secondary-button" onClick={openHistory} disabled={busy}><History size={16} /> Geçmiş</button>
        <button className="secondary-button" onClick={() => setProtectOpen(true)} disabled={busy}><LockKeyhole size={16} /> Koru</button>
        <button className="secondary-button" onClick={exportWord} disabled={busy}><FileDown size={16} /> Word</button>
        <button className="secondary-button" onClick={exportExcel} disabled={busy} title="Excel olarak dışa aktar"><FileSpreadsheet size={16} /> Excel</button>
        <button className="secondary-button" onClick={exportPowerPoint} disabled={busy} title="PowerPoint olarak dışa aktar"><Presentation size={16} /> PPT</button>
        <button className="secondary-button" onClick={exportImages} disabled={busy}><Images size={16} /> PNG</button>
        <button className="secondary-button" onClick={() => setCompressionOpen(true)} disabled={busy}><Shrink size={16} /> Sıkıştır</button>
        <button className="primary-button" onClick={download} disabled={busy}><Download size={16} /> Dışa aktar</button>
      </div>
    </header>

    <div className="editor-toolbar">
      <div className="tool-group">
        <button className={`tool-button ${mode === 'edit' ? 'active' : ''}`} onClick={() => chooseMode('edit')}><MousePointer2 size={17} /> Düzenle</button>
        <button className={`tool-button ${mode === 'addText' ? 'active' : ''}`} onClick={() => chooseMode('addText')}><Type size={17} /> Metin ekle</button>
        <button className={`tool-button ${mode === 'addImage' ? 'active' : ''}`} onClick={chooseImage}><ImagePlus size={17} /> Görsel</button>
        <button className={`tool-button ${mode === 'shape' ? 'active' : ''}`} onClick={() => chooseMode('shape')}><Square size={17} /> Şekil</button>
        <button className={`tool-button ${mode === 'draw' ? 'active' : ''}`} onClick={() => chooseMode('draw')}><PenLine size={17} /> Çiz</button>
        <button className="tool-button" onClick={() => setSignatureOpen(true)}><Signature size={17} /> İmza</button>
        <button className={`tool-button ${mode === 'link' ? 'active' : ''}`} onClick={() => chooseMode('link')}><Link2 size={17} /> Bağlantı</button>
        <button className="tool-button" onClick={() => setWatermarkOpen(true)}><Stamp size={17} /> Filigran</button>
        <button className={`tool-button danger ${mode === 'redact' ? 'active' : ''}`} onClick={() => chooseMode('redact')}><ShieldX size={17} /> Redaksiyon</button>
        <button className={`tool-button ${mode === 'crop' ? 'active' : ''}`} onClick={() => chooseMode('crop')}><Crop size={17} /> Kırp</button>
        <button className="tool-button" onClick={() => { setSearchOpen(true); setMatchCount(null) }} disabled={busy}><Search size={17} /> Bul / Değiştir</button>
        <button className="tool-button" onClick={undo} disabled={busy}><Undo2 size={17} /> Geri al</button>
        <button className="tool-button" onClick={redo} disabled={busy}><Redo2 size={17} /> İleri al</button>
        <button className="tool-button" onClick={rotate}><RotateCw size={17} /> Döndür</button>
        <button className="tool-button" onClick={() => setPageDecorOpen(true)} disabled={busy}><ListOrdered size={17} /> Sayfa bilgileri</button>
      </div>
      <span className="toolbar-divider" />
      <div className="zoom-controls"><button onClick={() => setZoom((z) => Math.max(.45, z - .1))}><Minus size={15} /></button><span>{Math.round(zoom * 100)}%</span><button onClick={() => setZoom((z) => Math.min(1.8, z + .1))}><Plus size={15} /></button></div>
      <button className="tool-button" onClick={() => setZoom(.9)}><Maximize2 size={17} /> Sayfaya sığdır</button>
      <div className="page-controls"><button disabled={page === 0} onClick={() => setPage(page - 1)}><ChevronLeft size={16} /></button><span><b>{page + 1}</b> / {pdf.page_count}</span><button disabled={page + 1 === pdf.page_count} onClick={() => setPage(page + 1)}><ChevronRight size={16} /></button></div>
    </div>

    <div className="editor-layout">
      <aside className="page-sidebar">
        <div className="panel-heading"><span>Sayfalar</span><PanelLeftClose size={16} /></div>
        <div className="thumbnail-list">{pdf.pages.map((item) => <div draggable={!busy} onDragStart={() => setDraggedPage(item.index)} onDragEnd={() => setDraggedPage(null)} onDragOver={(event) => event.preventDefault()} onDrop={() => dropPage(item.index)} className={`thumbnail-item ${page === item.index ? 'selected' : ''} ${draggedPage === item.index ? 'dragging' : ''}`} key={`${cacheKey}-${item.index}`}>
          <button className="thumbnail-preview" onClick={() => setPage(item.index)}><img src={renderUrl(document.id, item.index, cacheKey)} alt={`${item.number}. sayfa`} /><span>{item.number}</span></button>
          <div className="thumbnail-actions"><button aria-label="Sayfayı yukarı taşı" disabled={busy || item.index === 0} onClick={() => movePage(item.index, -1)}><ArrowUp size={12} /></button><button aria-label="Sayfayı aşağı taşı" disabled={busy || item.index === pdf.page_count - 1} onClick={() => movePage(item.index, 1)}><ArrowDown size={12} /></button><button aria-label="Sayfayı sil" disabled={busy || pdf.page_count === 1} onClick={() => removePage(item.index)}><Trash2 size={12} /></button></div>
        </div>)}<button className="add-blank-page" onClick={addBlankPage} disabled={busy}><Plus size={15} /> Boş sayfa ekle</button></div>
      </aside>

      <section className="canvas-area">
        {pdf.scanned_likely && <div className="scan-warning"><Search size={16} /><span>Bu belge taranmış olabilir. Türkçe + İngilizce OCR ile seçilebilir metin katmanı oluşturabilirsiniz.</span><button onClick={applyOcr} disabled={busy}>OCR uygula</button></div>}
        <div ref={pageElementRef} className={`pdf-page mode-${mode}`} style={viewport} onPointerDown={startArea} onPointerMove={updateArea} onPointerUp={finishArea}>
          <img src={renderUrl(document.id, page, cacheKey)} alt={`${page + 1}. sayfa`} style={viewport} />
          {pageImages.map((image) => { const box = selectedImage?.id === image.id && editRect ? editRect : image.bbox; return <button key={image.id} aria-label={`Görseli taşı: ${image.pixel_width} × ${image.pixel_height}`}
            onClick={() => clickImageElement(image)} onPointerDown={(event) => startImageDrag(event, image)} onPointerMove={updateImageDrag} onPointerUp={finishImageDrag} onPointerCancel={cancelImageDrag}
            className={`image-hitbox ${selectedImage?.id === image.id ? 'selected' : ''} ${draggingImageId === image.id ? 'dragging' : ''}`}
            style={{ left: box[0] * zoom, top: box[1] * zoom, width: (box[2] - box[0]) * zoom, height: (box[3] - box[1]) * zoom }} /> })}
          {blocks.map((block) => { const box = selected?.id === block.id && editRect ? editRect : block.bbox; return <button key={block.id} aria-label={`Metni düzenle: ${block.text.slice(0, 30)}`}
            onClick={() => clickTextBlock(block)} onPointerDown={(event) => startTextDrag(event, block)} onPointerMove={updateTextDrag} onPointerUp={finishTextDrag} onPointerCancel={cancelTextDrag}
            className={`text-hitbox ${selected?.id === block.id ? 'selected' : ''} ${draggingTextId === block.id ? 'dragging' : ''}`}
            style={{ left: box[0] * zoom, top: box[1] * zoom, width: (box[2] - box[0]) * zoom, height: (box[3] - box[1]) * zoom }} /> })}
          {draftRect && <div className={`draft-area ${mode}`} style={{ left: draftRect[0] * zoom, top: draftRect[1] * zoom, width: (draftRect[2] - draftRect[0]) * zoom, height: (draftRect[3] - draftRect[1]) * zoom }} />}
          {inkPath.length > 1 && <svg className="ink-preview" width={viewport.width} height={viewport.height}><polyline points={inkPath.map(([x, y]) => `${x * zoom},${y * zoom}`).join(' ')} fill="none" stroke={color} strokeWidth={2 * zoom} strokeLinecap="round" strokeLinejoin="round" /></svg>}
        </div>
      </section>

      <aside className="properties-panel">
        <div className="panel-heading"><span>Özellikler</span><Settings2 size={16} /></div>
        {selected && mode === 'edit' ? <div className="properties-form">
          <div className="selected-label"><Type size={16} /><span>Metin bloğu</span></div>
          <label>Metin<textarea value={text} onChange={(event) => setText(event.target.value)} rows={7} /></label>
          <div className="form-row"><label>Boyut<input type="number" min="4" max="144" value={fontSize} onChange={(event) => setFontSize(Number(event.target.value))} /></label><label>Renk<input type="color" value={color} onChange={(event) => setColor(event.target.value)} /></label></div>
          <div className="text-style-controls"><button className={bold ? 'active' : ''} onClick={() => setBold(!bold)} aria-label="Kalın"><b>B</b></button><button className={italic ? 'active' : ''} onClick={() => setItalic(!italic)} aria-label="İtalik"><i>I</i></button><button className={underline ? 'active' : ''} onClick={() => setUnderline(!underline)} aria-label="Altı çizili"><u>U</u></button><select aria-label="Metin hizalama" value={align} onChange={(event) => setAlign(event.target.value as typeof align)}><option value="left">Sola hizala</option><option value="center">Ortala</option><option value="right">Sağa hizala</option><option value="justify">İki yana yasla</option></select></div>
          {editRect && <><div className="field-caption">Konum ve alan (pt)</div><div className="position-grid"><label>X<input type="number" value={Math.round(editRect[0])} onChange={(event) => updateEditRect('x', Number(event.target.value))} /></label><label>Y<input type="number" value={Math.round(editRect[1])} onChange={(event) => updateEditRect('y', Number(event.target.value))} /></label><label>Genişlik<input type="number" min="8" value={Math.round(editRect[2] - editRect[0])} onChange={(event) => updateEditRect('width', Number(event.target.value))} /></label><label>Yükseklik<input type="number" min="8" value={Math.round(editRect[3] - editRect[1])} onChange={(event) => updateEditRect('height', Number(event.target.value))} /></label></div></>}
          <label>Yazı tipi<select value={fontFamily} onChange={(event) => setFontFamily(event.target.value)}>{!["Arial", "Times New Roman", "Courier New", "Segoe UI", "Calibri"].includes(fontFamily) && <option value={fontFamily}>{fontFamily}</option>}<option>Arial</option><option>Times New Roman</option><option>Courier New</option><option>Segoe UI</option><option>Calibri</option></select></label>
          <div className="style-clipboard-actions"><button className="secondary-button" onClick={copyTextStyle}><Copy size={15} /> Biçimi kopyala</button><button className="secondary-button" onClick={pasteTextStyle} disabled={!copiedTextStyle}><ClipboardPaste size={15} /> Biçimi yapıştır</button></div>
          {copiedTextStyle && <div className="copied-style-preview"><span className="style-color-dot" style={{ background: copiedTextStyle.color }} /><div><strong>{copiedTextStyle.fontFamily} · {copiedTextStyle.fontSize} pt</strong><small>{[copiedTextStyle.bold && 'Kalın', copiedTextStyle.italic && 'İtalik', copiedTextStyle.underline && 'Altı çizili'].filter(Boolean).join(' · ') || 'Normal'}</small></div></div>}
          <div className="drag-tip"><MousePointer2 size={16} /><span>Kutuyu sayfa üzerinde tutup sürükleyin; bıraktığınız konum otomatik kaydedilir.</span></div>
          <div className="security-note"><Save size={16} /><span>Eski içerik PDF akışından kalıcı olarak silinir; yalnızca üzeri kapatılmaz.</span></div>
          <button className="primary-button full" onClick={applyEdit} disabled={busy}>{busy ? <LoaderCircle className="spin" size={17} /> : <Save size={17} />} Değişikliği uygula</button>
        </div> : selectedImage && editRect && mode === 'edit' ? <div className="properties-form">
          <div className="selected-label image"><Images size={16} /><span>Görsel nesnesi</span></div>
          <div className="object-metrics"><span>Piksel</span><strong>{selectedImage.pixel_width} × {selectedImage.pixel_height}</strong><span>Sayfa alanı</span><strong>{Math.round(editRect[2] - editRect[0])} × {Math.round(editRect[3] - editRect[1])} pt</strong></div>
          <div className="drag-tip image"><MousePointer2 size={16} /><span>Görseli tutup sürükleyin; bıraktığınız konum otomatik kaydedilir.</span></div>
          <div className="security-note"><Undo2 size={16} /><span>Taşıma işlemini üst araç çubuğundaki Geri al düğmesiyle geri alabilirsiniz.</span></div>
        </div> : draftRect && mode !== 'edit' ? <div className="properties-form">
          <div className={`selected-label ${mode === 'redact' ? 'danger' : ''}`}>{mode === 'addText' ? <Type size={16} /> : mode === 'addImage' ? <ImagePlus size={16} /> : mode === 'shape' ? <Square size={16} /> : mode === 'crop' ? <Crop size={16} /> : mode === 'link' ? <Link2 size={16} /> : <ShieldX size={16} />}<span>{mode === 'addText' ? 'Yeni metin' : mode === 'addImage' ? 'Yeni görsel' : mode === 'shape' ? 'Yeni şekil' : mode === 'crop' ? 'Sayfayı kırp' : mode === 'link' ? 'Bağlantı alanı' : 'Kalıcı redaksiyon'}</span></div>
          {mode === 'addText' && <><label>Metin<textarea value={text} onChange={(event) => setText(event.target.value)} rows={6} /></label><div className="form-row"><label>Boyut<input type="number" min="4" max="144" value={fontSize} onChange={(event) => setFontSize(Number(event.target.value))} /></label><label>Renk<input type="color" value={color} onChange={(event) => setColor(event.target.value)} /></label></div><label>Yazı tipi<select value={fontFamily} onChange={(event) => setFontFamily(event.target.value)}>{!["Arial", "Times New Roman", "Courier New", "Segoe UI", "Calibri"].includes(fontFamily) && <option value={fontFamily}>{fontFamily}</option>}<option>Arial</option><option>Times New Roman</option><option>Courier New</option><option>Segoe UI</option><option>Calibri</option></select></label><div className="text-style-controls"><button className={bold ? 'active' : ''} onClick={() => setBold(!bold)}><b>B</b></button><button className={italic ? 'active' : ''} onClick={() => setItalic(!italic)}><i>I</i></button><button className={underline ? 'active' : ''} onClick={() => setUnderline(!underline)}><u>U</u></button><select value={align} onChange={(event) => setAlign(event.target.value as typeof align)}><option value="left">Sola hizala</option><option value="center">Ortala</option><option value="right">Sağa hizala</option><option value="justify">İki yana yasla</option></select></div><div className="style-clipboard-actions"><button className="secondary-button" onClick={pasteTextStyle} disabled={!copiedTextStyle}><ClipboardPaste size={15} /> Kopyalanan biçimi yapıştır</button></div>{copiedTextStyle && <div className="copied-style-preview"><span className="style-color-dot" style={{ background: copiedTextStyle.color }} /><div><strong>{copiedTextStyle.fontFamily} · {copiedTextStyle.fontSize} pt</strong><small>{[copiedTextStyle.bold && 'Kalın', copiedTextStyle.italic && 'İtalik', copiedTextStyle.underline && 'Altı çizili'].filter(Boolean).join(' · ') || 'Normal'}</small></div></div>}</>}
          {mode === 'addImage' && <div className="image-file-chip"><ImagePlus size={18} /><div><strong>{imageFile?.name || 'Görsel seçilmedi'}</strong><span>{imageFile ? `${(imageFile.size / 1024).toFixed(0)} KB` : 'Araç çubuğundan yeniden seçin'}</span></div></div>}
          {mode === 'shape' && <><label>Şekil<select value={shapeKind} onChange={(event) => setShapeKind(event.target.value as typeof shapeKind)}><option value="rectangle">Dikdörtgen</option><option value="ellipse">Elips</option><option value="line">Çizgi</option></select></label><label>Çizgi rengi<input type="color" value={color} onChange={(event) => setColor(event.target.value)} /></label></>}
          {mode === 'redact' && <div className="redaction-warning"><ShieldX size={18} /><span>Seçilen alandaki metin ve görsel pikseller PDF içeriğinden kalıcı olarak kaldırılır. Bu işlem dışa aktarılan dosyada geri alınamaz.</span></div>}
          {mode === 'crop' && <div className="security-note"><Crop size={18} /><span>Seçilen alan yeni görünür sayfa sınırı olur.</span></div>}
          {mode === 'link' && <label>Bağlantı adresi<input value={linkUrl} onChange={(event) => setLinkUrl(event.target.value)} placeholder="https://" /></label>}
          <div className="selection-size">Alan: {Math.round(draftRect[2] - draftRect[0])} × {Math.round(draftRect[3] - draftRect[1])} pt</div>
          <button className={`primary-button full ${mode === 'redact' ? 'danger-button' : ''}`} onClick={applyCanvasAction} disabled={busy || (mode === 'addText' && !text.trim()) || (mode === 'addImage' && !imageFile) || (mode === 'link' && !/^(https?:\/\/|mailto:)/i.test(linkUrl))}>{busy ? <LoaderCircle className="spin" size={17} /> : <Save size={17} />}{mode === 'redact' ? ' Kalıcı olarak redakte et' : ' PDF’ye uygula'}</button>
        </div> : <div className="empty-properties"><span>{mode === 'edit' ? <MousePointer2 size={24} /> : mode === 'addImage' ? <ImagePlus size={24} /> : mode === 'redact' ? <ShieldX size={24} /> : <Square size={24} />}</span><strong>{mode === 'edit' ? 'Bir öğe seçin' : mode === 'addImage' && !imageFile ? 'Bir görsel seçin' : 'Sayfada bir alan çizin'}</strong><p>{mode === 'edit' ? 'Mavi metin kutusunu veya turuncu görsel alanını tutup sürükleyin.' : mode === 'addImage' && !imageFile ? 'Araç çubuğundaki Görsel düğmesiyle PNG, JPG veya WebP seçin.' : 'Aracı uygulamak istediğiniz alanı fareyle sürükleyerek belirleyin.'}</p></div>}
        <div className="split-box"><div><Scissors size={16} /><strong>PDF’yi böl</strong></div><p>Noktalı virgülle çıktı grupları: <code>1-2; 3-5</code></p><input value={splitSpec} onChange={(e) => setSplitSpec(e.target.value)} /><button className="secondary-button full" onClick={split} disabled={busy}>ZIP olarak çıkar</button></div>
      </aside>
    </div>
    {busy && <div className="busy-indicator"><LoaderCircle className="spin" size={18} /> {activeJob ? `Arka planda işleniyor · %${activeJob.progress}` : 'İşleniyor…'}{activeJob && <button onClick={() => cancelLocalJob(activeJob.id)}>İptal</button>}</div>}
    <input ref={imageInput} className="visually-hidden" type="file" accept="image/png,image/jpeg,image/webp,image/bmp,image/tiff" onChange={receiveImage} />
    {protectOpen && <div className="modal-backdrop"><section className="dialog-card" role="dialog" aria-modal="true" aria-label="PDF koruma"><button className="dialog-close" onClick={() => setProtectOpen(false)}><X size={17} /></button><span className="dialog-icon"><LockKeyhole size={24} /></span><h2>Şifreli kopya oluştur</h2><p>Çalışma belgesi açık kalır; AES-256 ile korunan ayrı bir PDF kaydedilir.</p><label>Parola<input autoFocus type="password" minLength={4} value={protectPassword} onChange={(event) => setProtectPassword(event.target.value)} /></label><div className="security-note"><LockKeyhole size={16} /><span>Yazdırmaya izin verilir; kopyalama ve açıklama ekleme kapatılır.</span></div><button className="primary-button full" onClick={protect} disabled={busy || protectPassword.length < 4}>Şifreli kopyayı kaydet</button></section></div>}
    {metadataOpen && <div className="modal-backdrop"><section className="dialog-card" role="dialog" aria-modal="true" aria-label="PDF bilgileri"><button className="dialog-close" onClick={() => setMetadataOpen(false)}><X size={17} /></button><span className="dialog-icon"><FileCog size={24} /></span><h2>PDF dosya bilgileri</h2><p>Başlık, yazar, konu ve anahtar kelimeler PDF metadata alanına yazılır.</p><label>Başlık<input autoFocus value={metadata.title} onChange={(event) => setMetadata({ ...metadata, title: event.target.value })} /></label><label>Yazar<input value={metadata.author} onChange={(event) => setMetadata({ ...metadata, author: event.target.value })} /></label><label>Konu<input value={metadata.subject} onChange={(event) => setMetadata({ ...metadata, subject: event.target.value })} /></label><label>Anahtar kelimeler<input value={metadata.keywords} onChange={(event) => setMetadata({ ...metadata, keywords: event.target.value })} /></label><button className="primary-button full" onClick={saveMetadata} disabled={busy}>Bilgileri kaydet</button></section></div>}
    {compressionOpen && <div className="modal-backdrop"><section className="dialog-card" role="dialog" aria-modal="true" aria-label="PDF sıkıştırma"><button className="dialog-close" onClick={() => setCompressionOpen(false)}><X size={17} /></button><span className="dialog-icon"><Shrink size={24} /></span><h2>PDF sıkıştırma</h2><p>Sayfalar rasterize edilmez. PDF nesneleri temizlenir ve seçilen seviyede uygun gömülü görseller optimize edilir.</p><div className="compression-options">{[
      { value: 'quality', title: 'Yüksek kalite', text: 'Yalnızca kayıpsız nesne temizleme' },
      { value: 'balanced', title: 'Dengeli', text: 'Görseller 1800 px / %78 kalite' },
      { value: 'small', title: 'Küçük dosya', text: 'Görseller 1200 px / %55 kalite' },
    ].map((option) => <button key={option.value} className={compressionLevel === option.value ? 'selected' : ''} onClick={() => setCompressionLevel(option.value as typeof compressionLevel)}><strong>{option.title}</strong><span>{option.text}</span></button>)}</div><button className="primary-button full" onClick={compress} disabled={busy}>Sıkıştırmayı uygula</button></section></div>}
    {searchOpen && <div className="modal-backdrop"><section className="dialog-card" role="dialog" aria-modal="true" aria-label="PDF metninde bul ve değiştir"><button className="dialog-close" onClick={() => setSearchOpen(false)}><X size={17} /></button><span className="dialog-icon"><Search size={24} /></span><h2>Bul ve değiştir</h2><p>Metin katmanındaki tüm eşleşmeler aranır. Değiştirme sırasında eski içerik PDF akışından redaksiyonla kaldırılır.</p><label>Aranan metin<input autoFocus value={searchQuery} onChange={(event) => { setSearchQuery(event.target.value); setMatchCount(null) }} onKeyDown={(event) => event.key === 'Enter' && findText()} /></label><label>Yeni metin<input value={replacement} onChange={(event) => setReplacement(event.target.value)} placeholder="Boş bırakırsanız eşleşmeler silinir" /></label><div className="search-options"><label><input type="checkbox" checked={caseSensitive} onChange={(event) => { setCaseSensitive(event.target.checked); setMatchCount(null) }} /> Büyük/küçük harfe duyarlı</label><label><input type="checkbox" checked={wholeWord} onChange={(event) => { setWholeWord(event.target.checked); setMatchCount(null) }} /> Yalnızca tam sözcük</label></div>{matchCount !== null && <div className={`search-result ${matchCount ? 'found' : ''}`}>{matchCount ? `${matchCount} eşleşme bulundu` : 'Eşleşme bulunamadı'}</div>}<div className="dialog-actions"><button className="secondary-button" onClick={findText} disabled={busy || !searchQuery.trim()}>Tümünü bul</button><button className="primary-button" onClick={replaceAll} disabled={busy || !searchQuery.trim() || matchCount === 0}>Tümünü değiştir</button></div></section></div>}
    {pageDecorOpen && <div className="modal-backdrop"><section className="dialog-card" role="dialog" aria-modal="true" aria-label="Sayfa bilgileri"><button className="dialog-close" onClick={() => setPageDecorOpen(false)}><X size={17} /></button><span className="dialog-icon"><ListOrdered size={24} /></span><h2>Sayfa bilgileri</h2><p>Tüm sayfalara üstbilgi, altbilgi ve sayfa numarası ekleyin.</p><label>Üstbilgi<input autoFocus value={headerText} onChange={(event) => setHeaderText(event.target.value)} /></label><label>Altbilgi<input value={footerText} onChange={(event) => setFooterText(event.target.value)} /></label><div className="search-options"><label><input type="checkbox" checked={pageNumbers} onChange={(event) => setPageNumbers(event.target.checked)} /> Sayfa numarası ekle</label></div>{pageNumbers && <label>Başlangıç<input type="number" min="0" value={startNumber} onChange={(event) => setStartNumber(Number(event.target.value))} /></label>}<button className="primary-button full" onClick={applyPageDecor} disabled={busy || (!headerText.trim() && !footerText.trim() && !pageNumbers)}>Tüm sayfalara uygula</button></section></div>}
    {signatureOpen && <div className="modal-backdrop"><section className="dialog-card signature-dialog" role="dialog" aria-modal="true" aria-label="İmza çiz"><button className="dialog-close" onClick={() => setSignatureOpen(false)}><X size={17} /></button><span className="dialog-icon"><Signature size={24} /></span><h2>İmzanızı çizin</h2><p>İmza yalnızca bu cihazda PNG katmanı olarak oluşturulur. Kaydettikten sonra sayfada yerleştireceğiniz alanı çizin.</p><SignaturePad onSave={(file) => { setImageFile(file); setSignatureOpen(false); chooseMode('addImage') }} /></section></div>}
    {historyOpen && <div className="modal-backdrop"><section className="dialog-card" role="dialog" aria-modal="true" aria-label="İşlem geçmişi"><button className="dialog-close" onClick={() => setHistoryOpen(false)}><X size={17} /></button><span className="dialog-icon"><History size={24} /></span><h2>İşlem geçmişi</h2><p>Yalnızca işlem türü ve zamanı yerel çalışma alanında tutulur; belge içeriği loglanmaz.</p><div className="history-list">{historyItems.length ? historyItems.map((item, index) => <div key={`${item.timestamp}-${index}`}><History size={15} /><span><strong>{item.operation}</strong><small>{new Date(item.timestamp * 1000).toLocaleString('tr-TR')}</small></span></div>) : <div className="empty-history">Henüz kayıtlı işlem yok.</div>}</div></section></div>}
    {watermarkOpen && <div className="modal-backdrop"><section className="dialog-card" role="dialog" aria-modal="true" aria-label="Filigran"><button className="dialog-close" onClick={() => setWatermarkOpen(false)}><X size={17} /></button><span className="dialog-icon"><Stamp size={24} /></span><h2>Filigran</h2><p>Tüm sayfalara yarı saydam, daha sonra Atelier Docs ile kaldırılabilen filigran eklenir.</p><label>Filigran metni<input autoFocus value={watermarkText} onChange={(event) => setWatermarkText(event.target.value)} /></label><div className="dialog-actions"><button className="secondary-button" onClick={removeWatermark} disabled={busy}>Mevcut filigranı kaldır</button><button className="primary-button" onClick={applyWatermark} disabled={busy || !watermarkText.trim()}>Filigran ekle</button></div></section></div>}
    {toast && <Toast {...toast} onClose={() => setToast(null)} />}
  </main>
}
