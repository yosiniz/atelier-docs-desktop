import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowDown, ArrowLeft, ArrowUp, Download, FileDown, FileSpreadsheet, LoaderCircle, Plus, Save, Table2, Trash2 } from 'lucide-react'
import { Brand } from '../components/Brand'
import { Toast } from '../components/Toast'
import { convertOfficeToPdf, downloadDocument, inspectOffice, saveBlob, saveOffice } from '../lib/api'
import { useAppStore } from '../store'

type OfficeData = {
  type: 'document' | 'spreadsheet' | 'presentation'
  paragraphs?: { index: number; text: string; style: string }[]
  tables?: { index: number; rows: string[][] }[]
  sheets?: { name: string; rows: unknown[][]; truncated: boolean }[]
  slides?: { index: number; texts: { shape: number; text: string; name: string }[] }[]
}

const columnName = (index: number) => {
  let value = index + 1; let result = ''
  while (value) { value--; result = String.fromCharCode(65 + value % 26) + result; value = Math.floor(value / 26) }
  return result
}

export function OfficeEditorPage() {
  const navigate = useNavigate()
  const document = useAppStore((state) => state.document)
  const [data, setData] = useState<OfficeData | null>(null)
  const [sheetIndex, setSheetIndex] = useState(0)
  const [slideIndex, setSlideIndex] = useState(0)
  const [busy, setBusy] = useState(false)
  const [toast, setToast] = useState<{ message: string; kind: 'success' | 'error' } | null>(null)

  const load = async () => {
    if (!document) return
    setBusy(true)
    try { setData(await inspectOffice(document.id) as OfficeData) }
    catch (error) { setToast({ message: error instanceof Error ? error.message : 'Office dosyası açılamadı', kind: 'error' }) }
    finally { setBusy(false) }
  }
  useEffect(() => { if (!document || document.kind !== 'office') navigate('/'); else void load() }, [document?.id])

  const update = (recipe: (draft: OfficeData) => void) => setData((current) => {
    if (!current) return current
    const draft = structuredClone(current); recipe(draft); return draft
  })
  const updates = useMemo(() => {
    if (!data || !document) return []
    if (data.type === 'document') return [
      ...(data.paragraphs || []).map((item) => ({ kind: 'paragraph', index: item.index, value: item.text })),
      ...(data.tables || []).flatMap((table) => table.rows.flatMap((row, rowIndex) => row.map((value, column) => ({ kind: 'table', table: table.index, row: rowIndex, column, value })))),
    ]
    if (data.type === 'spreadsheet') return (data.sheets || []).flatMap((sheet) => sheet.rows.flatMap((row, rowIndex) => row.map((value, column) => document.name.toLowerCase().endsWith('.csv')
      ? { row: rowIndex, column, value: value ?? '' }
      : { sheet: sheet.name, cell: `${columnName(column)}${rowIndex + 1}`, value: value ?? '' })))
    return (data.slides || []).flatMap((slide) => slide.texts.map((item) => ({ slide: slide.index, shape: item.shape, value: item.text })))
  }, [data, document])

  const persist = async () => {
    if (!document) return
    setBusy(true)
    try { setData(await saveOffice(document.id, updates) as OfficeData); setToast({ message: 'Değişiklikler Office dosyasına kaydedildi.', kind: 'success' }) }
    catch (error) { setToast({ message: error instanceof Error ? error.message : 'Kaydetme başarısız', kind: 'error' }) }
    finally { setBusy(false) }
  }
  const download = async () => { if (document) await saveBlob(await downloadDocument(document.id), `duzenlenen-${document.name}`) }
  const exportPdf = async () => { if (document) await saveBlob(await convertOfficeToPdf(document.id), `${document.name.replace(/\.[^.]+$/, '')}.pdf`) }
  const performAction = async (actions: Record<string, unknown>[]) => {
    if (!document) return; setBusy(true)
    try { setData(await saveOffice(document.id, actions) as OfficeData); setSlideIndex(0); setToast({ message: 'Belge yapısı güncellendi.', kind: 'success' }) }
    catch (error) { setToast({ message: error instanceof Error ? error.message : 'İşlem başarısız', kind: 'error' }) }
    finally { setBusy(false) }
  }
  const moveSlide = (direction: -1 | 1) => {
    if (!data?.slides) return; const target = slideIndex + direction; if (target < 0 || target >= data.slides.length) return
    const order = data.slides.map((_, index) => index); [order[slideIndex], order[target]] = [order[target], order[slideIndex]]
    void performAction([{ kind: 'reorder', order }]).then(() => setSlideIndex(target))
  }

  if (!document) return null
  const sheet = data?.sheets?.[sheetIndex]
  const slide = data?.slides?.[slideIndex]
  return <main className="office-editor">
    <header className="editor-header"><button className="icon-button" onClick={() => navigate('/')}><ArrowLeft size={19} /></button><Brand /><span className="header-divider" /><div className="document-name"><FileSpreadsheet size={17} /><div><strong>{document.name}</strong><small>{data?.type || 'Yükleniyor'}</small></div></div><div className="editor-actions"><button className="secondary-button" onClick={persist} disabled={busy || !data}><Save size={16} /> Kaydet</button><button className="secondary-button" onClick={exportPdf} disabled={busy || !data}><FileDown size={16} /> PDF</button><button className="primary-button" onClick={download} disabled={busy || !data}><Download size={16} /> Dışa aktar</button></div></header>
    <div className="office-workspace">
      {busy && !data ? <div className="office-loading"><LoaderCircle className="spin" /> Dosya hazırlanıyor…</div> : data?.type === 'document' ? <section className="word-surface">
        {(data.paragraphs || []).map((paragraph) => <textarea key={paragraph.index} className={paragraph.style.startsWith('Heading') ? 'heading' : ''} value={paragraph.text} rows={Math.max(1, paragraph.text.split('\n').length)} onChange={(event) => update((draft) => { draft.paragraphs![paragraph.index].text = event.target.value })} />)}
        {(data.tables || []).map((table) => <table key={table.index}><tbody>{table.rows.map((row, rowIndex) => <tr key={rowIndex}>{row.map((cell, column) => <td key={column}><input value={cell} onChange={(event) => update((draft) => { draft.tables![table.index].rows[rowIndex][column] = event.target.value })} /></td>)}</tr>)}</tbody></table>)}<div className="office-structure-actions"><button className="secondary-button" onClick={() => performAction([...updates, { kind: 'add_paragraph', value: 'Yeni paragraf' }])}><Plus size={15} /> Paragraf ekle</button><button className="secondary-button" onClick={() => performAction([...updates, { kind: 'add_table', rows: 2, columns: 2 }])}><Table2 size={15} /> Tablo ekle</button></div>
      </section> : data?.type === 'spreadsheet' ? <section className="sheet-surface"><div className="sheet-tabs">{data.sheets?.map((item, index) => <button className={index === sheetIndex ? 'active' : ''} key={item.name} onClick={() => setSheetIndex(index)}>{item.name}</button>)}</div>{sheet?.truncated && <div className="scan-warning">Büyük çalışma sayfasının ilk 500 satır ve 50 sütunu gösteriliyor.</div>}<div className="sheet-grid"><table><thead><tr><th></th>{Array.from({ length: Math.max(1, ...((sheet?.rows || []).map((row) => row.length))) }, (_, index) => <th key={index}>{columnName(index)}</th>)}</tr></thead><tbody>{sheet?.rows.map((row, rowIndex) => <tr key={rowIndex}><th>{rowIndex + 1}</th>{row.map((cell, column) => <td key={column}><input value={String(cell ?? '')} onChange={(event) => update((draft) => { draft.sheets![sheetIndex].rows[rowIndex][column] = event.target.value })} /></td>)}</tr>)}</tbody></table></div><div className="office-structure-actions sheet-add"><button className="secondary-button" onClick={() => update((draft) => { const rows = draft.sheets![sheetIndex].rows; rows.push(Array(Math.max(1, rows[0]?.length || 1)).fill('')) })}><Plus size={15} /> Satır ekle</button><button className="secondary-button" onClick={() => update((draft) => { draft.sheets![sheetIndex].rows.forEach((row) => row.push('')) })}><Plus size={15} /> Sütun ekle</button></div></section> : data?.type === 'presentation' ? <section className="slides-workspace"><aside>{data.slides?.map((item, index) => <button key={item.index} className={index === slideIndex ? 'active' : ''} onClick={() => setSlideIndex(index)}>Slayt {index + 1}</button>)}<button onClick={() => performAction([{ kind: 'add_slide', value: 'Yeni Slayt' }])}><Plus size={14} /> Slayt ekle</button></aside><div className="slide-surface"><div className="slide-heading"><h3>Slayt {slideIndex + 1}</h3><div><button onClick={() => moveSlide(-1)} disabled={slideIndex === 0}><ArrowUp size={15} /></button><button onClick={() => moveSlide(1)} disabled={slideIndex + 1 === data.slides?.length}><ArrowDown size={15} /></button><button className="danger" onClick={() => performAction([{ kind: 'delete_slide', slide: slideIndex }])} disabled={(data.slides?.length || 0) <= 1}><Trash2 size={15} /></button></div></div>{slide?.texts.map((item, index) => <label key={item.shape}>{item.name}<textarea value={item.text} rows={4} onChange={(event) => update((draft) => { draft.slides![slideIndex].texts[index].text = event.target.value })} /></label>)}</div></section> : null}
    </div>{toast && <Toast {...toast} onClose={() => setToast(null)} />}
  </main>
}
