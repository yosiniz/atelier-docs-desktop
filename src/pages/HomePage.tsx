import { ChangeEvent, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight, Combine, FileDown, FileImage, FileOutput, FilePenLine, FileSpreadsheet, FileUp, FolderArchive,
  ImageDown, Images, Layers3, Moon, ScanText, Scissors, ShieldCheck, Sun, UploadCloud, Zap,
} from 'lucide-react'
import { Brand } from '../components/Brand'
import { Toast } from '../components/Toast'
import { batchCompressPdfs, batchConvertImages, convertDocxToPdf, convertImagesToPdf, convertPdfToDocx, convertPdfToImages, convertScansToSearchablePdf, mergePdfs, saveBlob, upload } from '../lib/api'
import { useAppStore } from '../store'

const tools = [
  { title: 'PDF Düzenle', text: 'Mevcut metinleri seçin, değiştirin ve kalıcı kaydedin.', icon: FilePenLine, tone: 'violet', action: 'pdf' },
  { title: 'PDF Birleştir', text: 'Birden çok PDF’i tek belgede birleştirin.', icon: Combine, tone: 'blue', action: 'merge' },
  { title: 'PDF Böl', text: 'Sayfa aralıklarını ayrı dosyalar halinde çıkarın.', icon: Scissors, tone: 'orange', action: 'pdf' },
  { title: 'PDF Sıkıştır', text: 'Gereksiz nesneleri temizleyerek boyutu azaltın.', icon: FileOutput, tone: 'green', action: 'pdf' },
  { title: 'Görsel Dönüştür', text: 'PNG, JPG ve WebP arasında yerel dönüşüm.', icon: Images, tone: 'pink', action: 'image' },
  { title: 'Görsel Düzenle', text: 'Renk, boyut, yön ve temel filtre ayarları.', icon: FileImage, tone: 'cyan', action: 'image' },
  { title: 'PDF → Word', text: 'Metinleri düzenlenebilir DOCX belgesine aktarın.', icon: FileDown, tone: 'blue', action: 'pdf-word' },
  { title: 'Word → PDF', text: 'DOCX içeriğini yerel motorla PDF’e dönüştürün.', icon: FileUp, tone: 'orange', action: 'docx-pdf' },
  { title: 'PDF → JPG', text: 'Her sayfayı yüksek kaliteli JPG olarak ZIP’e aktarın.', icon: ImageDown, tone: 'pink', action: 'pdf-images' },
  { title: 'JPG/PNG → PDF', text: 'Birden çok görseli sıralı PDF sayfalarına dönüştürün.', icon: FileOutput, tone: 'green', action: 'images-pdf' },
  { title: 'Tarama → OCR PDF', text: 'JPG, PNG veya TIFF taramalarını aranabilir ve düzenlenebilir PDF yapın.', icon: ScanText, tone: 'blue', action: 'scan-ocr' },
  { title: 'Office Araçları', text: 'Word, Excel, CSV ve PowerPoint dosyalarını düzenleyin.', icon: FileSpreadsheet, tone: 'violet', action: 'office' },
  { title: 'Toplu Görsel', text: 'Birden çok görseli tek seferde WebP biçimine dönüştürün.', icon: FolderArchive, tone: 'cyan', action: 'batch-image' },
  { title: 'Toplu PDF Sıkıştır', text: 'Birden çok PDF’i dengeli profille ZIP olarak hazırlayın.', icon: FolderArchive, tone: 'green', action: 'batch-pdf' },
]

export function HomePage() {
  const navigate = useNavigate()
  const input = useRef<HTMLInputElement>(null)
  const mergeInput = useRef<HTMLInputElement>(null)
  const imagesPdfInput = useRef<HTMLInputElement>(null)
  const scanOcrInput = useRef<HTMLInputElement>(null)
  const batchImageInput = useRef<HTMLInputElement>(null)
  const batchPdfInput = useRef<HTMLInputElement>(null)
  const [accept, setAccept] = useState('.pdf')
  const [intent, setIntent] = useState<'edit' | 'pdf-word' | 'docx-pdf' | 'pdf-images'>('edit')
  const [busy, setBusy] = useState(false)
  const [toast, setToast] = useState<{ message: string; kind: 'success' | 'error' } | null>(null)
  const setDocument = useAppStore((state) => state.setDocument)
  const theme = useAppStore((state) => state.theme)
  const toggleTheme = useAppStore((state) => state.toggleTheme)

  const pick = (kind: 'pdf' | 'image' | 'docx' | 'office', nextIntent: typeof intent = 'edit') => {
    setIntent(nextIntent)
    setAccept(kind === 'pdf' ? '.pdf' : kind === 'docx' ? '.docx' : kind === 'office' ? '.docx,.xlsx,.csv,.pptx' : 'image/*')
    requestAnimationFrame(() => input.current?.click())
  }

  const openFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setBusy(true)
    try {
      const uploaded = await upload(file)
      setDocument(uploaded)
      if (intent === 'pdf-word' && uploaded.kind === 'pdf') {
        await saveBlob(await convertPdfToDocx(uploaded.id), `${uploaded.name.replace(/\.pdf$/i, '')}.docx`)
        setToast({ message: 'PDF düzenlenebilir Word belgesine dönüştürüldü.', kind: 'success' })
      } else if (intent === 'docx-pdf' && uploaded.kind === 'office') {
        await saveBlob(await convertDocxToPdf(uploaded.id), `${uploaded.name.replace(/\.docx$/i, '')}.pdf`)
        setToast({ message: 'Word belgesi PDF’e dönüştürüldü.', kind: 'success' })
      } else if (intent === 'pdf-images' && uploaded.kind === 'pdf') {
        await saveBlob(await convertPdfToImages(uploaded.id, 'jpg'), `${uploaded.name.replace(/\.pdf$/i, '')}-jpg.zip`)
        setToast({ message: 'PDF sayfaları JPG olarak ZIP’e aktarıldı.', kind: 'success' })
      } else if (uploaded.kind === 'pdf') navigate('/pdf')
      else if (uploaded.kind === 'image') navigate('/image')
      else navigate('/office')
    } catch (error) {
      setToast({ message: error instanceof Error ? error.message : 'Dosya açılamadı', kind: 'error' })
    } finally { setBusy(false) }
  }

  const merge = async (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || [])
    event.target.value = ''
    if (files.length < 2) return setToast({ message: 'En az iki PDF seçmelisiniz.', kind: 'error' })
    setBusy(true)
    try {
      const blob = await mergePdfs(files)
      await saveBlob(blob, 'birlestirilmis.pdf')
      setToast({ message: `${files.length} PDF başarıyla birleştirildi.`, kind: 'success' })
    } catch (error) {
      setToast({ message: error instanceof Error ? error.message : 'Birleştirme başarısız', kind: 'error' })
    } finally { setBusy(false) }
  }

  const imagesToPdf = async (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || [])
    event.target.value = ''
    if (!files.length) return
    setBusy(true)
    try {
      await saveBlob(await convertImagesToPdf(files), 'gorseller.pdf')
      setToast({ message: `${files.length} görsel PDF’e dönüştürüldü.`, kind: 'success' })
    } catch (error) {
      setToast({ message: error instanceof Error ? error.message : 'Görseller dönüştürülemedi', kind: 'error' })
    } finally { setBusy(false) }
  }

  const scansToOcrPdf = async (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || [])
    event.target.value = ''
    if (!files.length) return
    setBusy(true)
    try {
      await saveBlob(await convertScansToSearchablePdf(files), 'aranabilir-tarama.pdf')
      setToast({ message: `${files.length} tarama OCR uygulanarak aranabilir PDF'e dönüştürüldü.`, kind: 'success' })
    } catch (error) {
      setToast({ message: error instanceof Error ? error.message : 'OCR PDF oluşturulamadı', kind: 'error' })
    } finally { setBusy(false) }
  }

  const batchFiles = async (event: ChangeEvent<HTMLInputElement>, kind: 'image' | 'pdf') => {
    const files = Array.from(event.target.files || []); event.target.value = ''
    if (!files.length) return
    setBusy(true)
    try {
      const blob = kind === 'image' ? await batchConvertImages(files) : await batchCompressPdfs(files)
      await saveBlob(blob, kind === 'image' ? 'toplu-gorseller.zip' : 'toplu-pdf.zip')
      setToast({ message: `${files.length} dosya toplu olarak işlendi.`, kind: 'success' })
    } catch (error) { setToast({ message: error instanceof Error ? error.message : 'Toplu işlem başarısız', kind: 'error' }) }
    finally { setBusy(false) }
  }

  return <main className="home-shell">
    <header className="home-header">
      <Brand />
      <div className="header-actions">
        <span className="privacy-pill"><ShieldCheck size={15} /> %100 yerel işlem</span>
        <button className="icon-button" onClick={toggleTheme} aria-label="Tema değiştir">{theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}</button>
      </div>
    </header>

    <section className="hero">
      <div className="eyebrow">MASAÜSTÜ BELGE ARAÇLARI</div>
      <h1>Belgeleriniz için<br /><span>sade bir çalışma alanı.</span></h1>
      <p>PDF, Office ve görsellerinizi buluta yüklemeden düzenleyin, dönüştürün ve dışa aktarın.</p>
      <div className={`drop-zone ${busy ? 'busy' : ''}`} onClick={() => pick('pdf')}>
        <div className="upload-icon"><UploadCloud size={27} /></div>
        <div><strong>{busy ? 'Dosya hazırlanıyor…' : 'Bir dosya seçin'}</strong><small>PDF veya görsel · En fazla 250 MB</small></div>
        <button className="primary-button" disabled={busy}>Dosya aç <ArrowRight size={17} /></button>
      </div>
      <div className="hero-meta"><span><Zap size={14} /> Hızlı yerel motor</span><span><ShieldCheck size={14} /> Dosyalar cihazınızda kalır</span><span><Layers3 size={14} /> Orijinal dosya korunur</span></div>
    </section>

    <section className="tools-section">
      <div className="section-title"><div><span>ÇALIŞMA ARAÇLARI</span><h2>Ne yapmak istersiniz?</h2></div><small>{tools.length} araç kullanılabilir</small></div>
      <div className="tool-grid">
        {tools.map((tool) => <button key={tool.title} disabled={busy} className="tool-card"
          onClick={() => tool.action === 'merge' ? mergeInput.current?.click()
            : tool.action === 'pdf-word' ? pick('pdf', 'pdf-word')
            : tool.action === 'docx-pdf' ? pick('docx', 'docx-pdf')
            : tool.action === 'pdf-images' ? pick('pdf', 'pdf-images')
            : tool.action === 'images-pdf' ? imagesPdfInput.current?.click()
            : tool.action === 'scan-ocr' ? scanOcrInput.current?.click()
            : tool.action === 'batch-image' ? batchImageInput.current?.click()
            : tool.action === 'batch-pdf' ? batchPdfInput.current?.click()
            : pick(tool.action as 'pdf' | 'image' | 'office')}>
          <span className={`tool-icon ${tool.tone}`}><tool.icon size={22} /></span>
          <span className="tool-copy"><strong>{tool.title}</strong><small>{tool.text}</small></span>
          <ArrowRight className="card-arrow" size={18} />
        </button>)}
      </div>
    </section>
    <input ref={input} className="visually-hidden" type="file" accept={accept} onChange={openFile} />
    <input ref={mergeInput} className="visually-hidden" type="file" accept=".pdf" multiple onChange={merge} />
    <input ref={imagesPdfInput} className="visually-hidden" type="file" accept="image/png,image/jpeg,image/webp,image/bmp,image/tiff" multiple onChange={imagesToPdf} />
    <input ref={scanOcrInput} className="visually-hidden" type="file" accept="image/png,image/jpeg,image/webp,image/bmp,image/tiff" multiple onChange={scansToOcrPdf} />
    <input ref={batchImageInput} className="visually-hidden" type="file" accept="image/png,image/jpeg,image/webp,image/bmp,image/tiff" multiple onChange={(event) => batchFiles(event, 'image')} />
    <input ref={batchPdfInput} className="visually-hidden" type="file" accept=".pdf" multiple onChange={(event) => batchFiles(event, 'pdf')} />
    {toast && <Toast {...toast} onClose={() => setToast(null)} />}
  </main>
}
