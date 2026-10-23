import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Download, FlipHorizontal2, Image as ImageIcon, Layers3, LoaderCircle, RotateCw, SlidersHorizontal } from 'lucide-react'
import { Brand } from '../components/Brand'
import { LayeredImageEditor } from '../components/LayeredImageEditor'
import { Toast } from '../components/Toast'
import { compressImage, convertImage, editImage, fileUrl, saveBlob } from '../lib/api'
import { useAppStore } from '../store'

export function ImageEditorPage() {
  const navigate = useNavigate()
  const document = useAppStore((state) => state.document)
  const [preview, setPreview] = useState<string | null>(null)
  const [brightness, setBrightness] = useState(100)
  const [contrast, setContrast] = useState(100)
  const [saturation, setSaturation] = useState(100)
  const [blur, setBlur] = useState(0)
  const [sharpen, setSharpen] = useState(0)
  const [grayscale, setGrayscale] = useState(false)
  const [sepia, setSepia] = useState(false)
  const [rotate, setRotate] = useState(0)
  const [flip, setFlip] = useState('none')
  const [format, setFormat] = useState('JPEG')
  const [quality, setQuality] = useState(86)
  const [targetKb, setTargetKb] = useState(500)
  const [cropX, setCropX] = useState(0)
  const [cropY, setCropY] = useState(0)
  const [cropWidth, setCropWidth] = useState(document?.image?.width || 1)
  const [cropHeight, setCropHeight] = useState(document?.image?.height || 1)
  const [busy, setBusy] = useState(false)
  const [workspaceMode, setWorkspaceMode] = useState<'adjust' | 'layers'>('adjust')
  const [toast, setToast] = useState<{ message: string; kind: 'success' | 'error' } | null>(null)

  useEffect(() => { if (!document || document.kind !== 'image') navigate('/') }, [document, navigate])
  const filter = useMemo(() => `brightness(${brightness}%) contrast(${contrast}%) saturate(${saturation}%) blur(${blur}px) grayscale(${grayscale ? 1 : 0}) sepia(${sepia ? 1 : 0})`, [brightness, contrast, saturation, blur, grayscale, sepia])
  if (!document?.image) return null
  const sourceUrl = fileUrl(document.id)

  const process = async (convert = false) => {
    setBusy(true)
    try {
      const blob = convert
        ? await convertImage(document.id, { output_format: format, quality: String(quality), background: '#ffffff' })
        : await editImage(document.id, {
          brightness: String(brightness / 100), contrast: String(contrast / 100), saturation: String(saturation / 100),
          blur: String(blur), sharpen: String(sharpen), grayscale: String(grayscale), sepia: String(sepia),
          rotate: String(rotate), flip, crop_x: String(cropX), crop_y: String(cropY),
          crop_width: String(cropWidth), crop_height: String(cropHeight),
        })
      if (convert) await saveBlob(blob, `donusturulen.${format === 'JPEG' ? 'jpg' : format.toLowerCase()}`)
      else {
        if (preview) URL.revokeObjectURL(preview)
        setPreview(URL.createObjectURL(blob)); await saveBlob(blob, 'duzenlenen.png')
      }
      setToast({ message: convert ? 'Görsel dönüştürüldü.' : 'Düzenlenen görsel kaydedildi.', kind: 'success' })
    } catch (error) { setToast({ message: error instanceof Error ? error.message : 'İşlem başarısız', kind: 'error' }) }
    finally { setBusy(false) }
  }

  const compressTarget = async () => {
    setBusy(true)
    try {
      const targetFormat = format === 'PNG' ? 'JPEG' : format
      const blob = await compressImage(document.id, { target_kb: String(targetKb), output_format: targetFormat })
      await saveBlob(blob, `sikistirilan.${targetFormat === 'JPEG' ? 'jpg' : 'webp'}`)
      const reached = Math.round(blob.size / 1024)
      setToast({ message: `Görsel ${reached} KB olarak kaydedildi${reached > targetKb ? '; hedef kalite sınırında kaldı' : ''}.`, kind: 'success' })
    } catch (error) { setToast({ message: error instanceof Error ? error.message : 'Sıkıştırma başarısız', kind: 'error' }) }
    finally { setBusy(false) }
  }

  return <main className="image-editor">
    <header className="editor-header"><button className="icon-button" onClick={() => navigate('/')}><ArrowLeft size={19} /></button><Brand /><span className="header-divider" /><div className="document-name"><ImageIcon size={17} /><div><strong>{document.name}</strong><small>{document.image.width} × {document.image.height} · {document.image.format}</small></div></div><div className="editor-actions"><button className={workspaceMode === 'adjust' ? 'secondary-button active' : 'secondary-button'} onClick={() => setWorkspaceMode('adjust')}><SlidersHorizontal size={16} /> Ayarlar</button><button className={workspaceMode === 'layers' ? 'secondary-button active' : 'secondary-button'} onClick={() => setWorkspaceMode('layers')}><Layers3 size={16} /> Katmanlar</button></div></header>
    {workspaceMode === 'layers' ? <LayeredImageEditor sourceUrl={sourceUrl} width={document.image.width} height={document.image.height} /> : <div className="image-workspace">
      <section className="image-canvas"><div className="checkerboard"><img src={preview || sourceUrl} alt="Düzenlenen görsel" style={{ filter, transform: `rotate(${rotate}deg) scaleX(${flip === 'horizontal' ? -1 : 1}) scaleY(${flip === 'vertical' ? -1 : 1})` }} /></div></section>
      <aside className="image-controls"><div className="panel-heading"><span><SlidersHorizontal size={16} /> Ayarlar</span></div>
        {[['Parlaklık', brightness, setBrightness, 0, 200], ['Kontrast', contrast, setContrast, 0, 200], ['Doygunluk', saturation, setSaturation, 0, 200], ['Bulanıklık', blur, setBlur, 0, 20], ['Keskinlik', sharpen, setSharpen, 0, 5]].map(([label, value, setter, min, max]) => <label className="range-field" key={label as string}><span>{label as string}<b>{value as number}{label === 'Bulanıklık' ? 'px' : label === 'Keskinlik' ? '' : '%'}</b></span><input type="range" min={min as number} max={max as number} step={label === 'Keskinlik' ? .1 : 1} value={value as number} onChange={(e) => (setter as (v: number) => void)(Number(e.target.value))} /></label>)}
        <div className="filter-toggles"><label><input type="checkbox" checked={grayscale} onChange={(event) => setGrayscale(event.target.checked)} /> Siyah-beyaz</label><label><input type="checkbox" checked={sepia} onChange={(event) => setSepia(event.target.checked)} /> Sepya</label></div>
        <div className="button-row"><button className="secondary-button" onClick={() => setRotate((v) => (v + 90) % 360)}><RotateCw size={16} /> Döndür</button><button className="secondary-button" onClick={() => setFlip(flip === 'horizontal' ? 'none' : 'horizontal')}><FlipHorizontal2 size={16} /> Çevir</button></div>
        <div className="control-divider" /><h3>Kırpma alanı</h3><div className="crop-grid"><label>X<input type="number" min="0" max={document.image.width - 1} value={cropX} onChange={(event) => setCropX(Number(event.target.value))} /></label><label>Y<input type="number" min="0" max={document.image.height - 1} value={cropY} onChange={(event) => setCropY(Number(event.target.value))} /></label><label>Genişlik<input type="number" min="1" max={document.image.width - cropX} value={cropWidth} onChange={(event) => setCropWidth(Number(event.target.value))} /></label><label>Yükseklik<input type="number" min="1" max={document.image.height - cropY} value={cropHeight} onChange={(event) => setCropHeight(Number(event.target.value))} /></label></div>
        <button className="primary-button full" disabled={busy} onClick={() => process(false)}>{busy ? <LoaderCircle className="spin" size={16} /> : <Download size={16} />} PNG olarak uygula ve kaydet</button>
        <div className="control-divider" /><h3>Format dönüştür</h3><div className="form-row"><label>Biçim<select value={format} onChange={(e) => setFormat(e.target.value)}><option>JPEG</option><option>PNG</option><option>WEBP</option></select></label><label>Kalite<input type="number" min="1" max="100" value={quality} onChange={(e) => setQuality(Number(e.target.value))} /></label></div>
        <button className="secondary-button full" disabled={busy} onClick={() => process(true)}>Dönüştür ve kaydet</button>
        <div className="control-divider" /><h3>Hedef dosya boyutu</h3><label>Hedef KB<input type="number" min="10" max="102400" value={targetKb} onChange={(event) => setTargetKb(Number(event.target.value))} /></label><p className="control-hint">Kalite mümkün olan en yüksek değerde tutularak hedefe yaklaşılır. PNG seçiliyse JPEG kullanılır.</p><button className="primary-button full" disabled={busy || targetKb < 10} onClick={compressTarget}>Hedef boyuta sıkıştır</button>
      </aside>
    </div>}{toast && <Toast {...toast} onClose={() => setToast(null)} />}
  </main>
}
