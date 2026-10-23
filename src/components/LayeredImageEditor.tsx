import { type PointerEvent, useCallback, useEffect, useRef, useState } from 'react'
import { ArrowDown, ArrowUp, Download, Plus, Redo2, Square, Trash2, Type, Undo2 } from 'lucide-react'
import { saveBlob } from '../lib/api'

type Layer = {
  id: string
  type: 'text' | 'rectangle'
  x: number
  y: number
  width: number
  height: number
  text?: string
  color: string
  fontSize?: number
}

export function LayeredImageEditor({ sourceUrl, width, height }: { sourceUrl: string; width: number; height: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const baseRef = useRef<HTMLImageElement | null>(null)
  const dragRef = useRef<{ id: string; dx: number; dy: number } | null>(null)
  const [layers, setLayers] = useState<Layer[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [past, setPast] = useState<string[]>([])
  const [future, setFuture] = useState<string[]>([])

  const render = useCallback((showSelection = true) => {
    const canvas = canvasRef.current; const base = baseRef.current
    if (!canvas || !base) return
    const context = canvas.getContext('2d'); if (!context) return
    context.clearRect(0, 0, width, height); context.drawImage(base, 0, 0, width, height)
    for (const layer of layers) {
      context.save(); context.fillStyle = layer.color; context.strokeStyle = layer.color
      if (layer.type === 'text') {
        context.font = `600 ${layer.fontSize || 36}px Inter, Arial, sans-serif`
        context.textBaseline = 'top'; context.fillText(layer.text || 'Metin', layer.x, layer.y)
      } else { context.lineWidth = Math.max(2, width / 500); context.strokeRect(layer.x, layer.y, layer.width, layer.height) }
      if (showSelection && layer.id === selectedId) {
        context.strokeStyle = '#315f54'; context.lineWidth = Math.max(2, width / 600); context.setLineDash([8, 6])
        context.strokeRect(layer.x - 5, layer.y - 5, layer.width + 10, layer.height + 10)
      }
      context.restore()
    }
  }, [height, layers, selectedId, width])

  useEffect(() => {
    const image = new Image(); image.crossOrigin = 'anonymous'
    image.onload = () => { baseRef.current = image; render() }
    image.src = sourceUrl
    return () => { image.onload = null }
  }, [sourceUrl])
  useEffect(render, [render])

  const checkpoint = () => { setPast((items) => [...items.slice(-29), JSON.stringify(layers)]); setFuture([]) }
  const addText = () => { checkpoint(); const id = crypto.randomUUID(); setLayers((items) => [...items, { id, type: 'text', x: width * .12, y: height * .12, width: width * .35, height: 52, text: 'Yeni metin', color: '#ffffff', fontSize: Math.max(18, Math.round(width / 18)) }]); setSelectedId(id) }
  const addRectangle = () => { checkpoint(); const id = crypto.randomUUID(); setLayers((items) => [...items, { id, type: 'rectangle', x: width * .2, y: height * .2, width: width * .35, height: height * .22, color: '#315f54' }]); setSelectedId(id) }
  const mutateSelected = (update: Partial<Layer>) => { if (!selectedId) return; checkpoint(); setLayers((items) => items.map((item) => item.id === selectedId ? { ...item, ...update } : item)) }
  const remove = () => { if (!selectedId) return; checkpoint(); setLayers((items) => items.filter((item) => item.id !== selectedId)); setSelectedId(null) }
  const reorder = (direction: -1 | 1) => { if (!selectedId) return; const index = layers.findIndex((item) => item.id === selectedId); const target = index + direction; if (target < 0 || target >= layers.length) return; checkpoint(); const next = [...layers]; [next[index], next[target]] = [next[target], next[index]]; setLayers(next) }
  const undo = () => { const previous = past.at(-1); if (previous === undefined) return; setFuture((items) => [JSON.stringify(layers), ...items]); setLayers(JSON.parse(previous)); setPast((items) => items.slice(0, -1)); setSelectedId(null) }
  const redo = () => { const next = future[0]; if (next === undefined) return; setPast((items) => [...items, JSON.stringify(layers)]); setLayers(JSON.parse(next)); setFuture((items) => items.slice(1)); setSelectedId(null) }

  const point = (event: PointerEvent<HTMLCanvasElement>) => { const bounds = event.currentTarget.getBoundingClientRect(); return { x: (event.clientX - bounds.left) * width / bounds.width, y: (event.clientY - bounds.top) * height / bounds.height } }
  const pointerDown = (event: PointerEvent<HTMLCanvasElement>) => {
    const cursor = point(event)
    const hit = [...layers].reverse().find((layer) => cursor.x >= layer.x && cursor.x <= layer.x + layer.width && cursor.y >= layer.y && cursor.y <= layer.y + layer.height)
    setSelectedId(hit?.id || null)
    if (hit) { checkpoint(); dragRef.current = { id: hit.id, dx: cursor.x - hit.x, dy: cursor.y - hit.y }; event.currentTarget.setPointerCapture(event.pointerId) }
  }
  const pointerMove = (event: PointerEvent<HTMLCanvasElement>) => {
    const drag = dragRef.current; if (!drag) return; const cursor = point(event)
    setLayers((items) => items.map((item) => item.id === drag.id ? { ...item, x: Math.max(0, Math.min(width - item.width, cursor.x - drag.dx)), y: Math.max(0, Math.min(height - item.height, cursor.y - drag.dy)) } : item))
  }
  const exportPng = async () => {
    const canvas = canvasRef.current; if (!canvas) return
    render(false); const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/png'))
    render(true); if (blob) await saveBlob(blob, 'katmanli-gorsel.png')
  }
  const selected = layers.find((item) => item.id === selectedId)
  return <div className="layer-editor">
    <section className="layer-stage"><canvas ref={canvasRef} width={width} height={height} onPointerDown={pointerDown} onPointerMove={pointerMove} onPointerUp={() => { dragRef.current = null }} /></section>
    <aside className="layer-panel"><div className="layer-tools"><button onClick={addText}><Type size={16} /> Metin</button><button onClick={addRectangle}><Square size={16} /> Şekil</button><button onClick={undo} disabled={!past.length}><Undo2 size={16} /></button><button onClick={redo} disabled={!future.length}><Redo2 size={16} /></button></div>
      {selected ? <div className="layer-properties"><strong>{selected.type === 'text' ? 'Metin katmanı' : 'Şekil katmanı'}</strong>{selected.type === 'text' && <><label>Metin<textarea value={selected.text} onFocus={checkpoint} onChange={(event) => setLayers((items) => items.map((item) => item.id === selected.id ? { ...item, text: event.target.value, width: Math.max(item.width, event.target.value.length * (item.fontSize || 36) * .55) } : item))} /></label><label>Boyut<input type="number" min="8" max="300" value={selected.fontSize} onChange={(event) => mutateSelected({ fontSize: Number(event.target.value), height: Number(event.target.value) * 1.3 })} /></label></>}<label>Renk<input type="color" value={selected.color} onChange={(event) => mutateSelected({ color: event.target.value })} /></label><div className="layer-order"><button onClick={() => reorder(-1)}><ArrowDown size={15} /> Alta</button><button onClick={() => reorder(1)}><ArrowUp size={15} /> Üste</button><button className="danger" onClick={remove}><Trash2 size={15} /> Sil</button></div></div> : <div className="empty-properties"><Plus size={22} /><strong>Katman ekleyin</strong><p>Metin veya şekil ekleyip tuval üzerinde sürükleyin.</p></div>}
      <div className="layer-list">{[...layers].reverse().map((layer) => <button className={layer.id === selectedId ? 'active' : ''} key={layer.id} onClick={() => setSelectedId(layer.id)}>{layer.type === 'text' ? <Type size={14} /> : <Square size={14} />} {layer.text || 'Dikdörtgen'}</button>)}</div><button className="primary-button full" onClick={exportPng}><Download size={16} /> Katmanlı PNG kaydet</button></aside>
  </div>
}
