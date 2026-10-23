import { type PointerEvent, useRef } from 'react'
import { Eraser, PenLine } from 'lucide-react'

export function SignaturePad({ onSave }: { onSave: (file: File) => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const drawing = useRef(false)
  const point = (event: PointerEvent<HTMLCanvasElement>) => { const rect = event.currentTarget.getBoundingClientRect(); return [(event.clientX - rect.left) * 900 / rect.width, (event.clientY - rect.top) * 280 / rect.height] }
  const start = (event: PointerEvent<HTMLCanvasElement>) => { const context = canvasRef.current?.getContext('2d'); if (!context) return; drawing.current = true; const [x, y] = point(event); context.beginPath(); context.moveTo(x, y); context.strokeStyle = '#111827'; context.lineWidth = 5; context.lineCap = 'round'; event.currentTarget.setPointerCapture(event.pointerId) }
  const move = (event: PointerEvent<HTMLCanvasElement>) => { if (!drawing.current) return; const context = canvasRef.current?.getContext('2d'); if (!context) return; const [x, y] = point(event); context.lineTo(x, y); context.stroke() }
  const save = () => canvasRef.current?.toBlob((blob) => blob && onSave(new File([blob], 'imza.png', { type: 'image/png' })), 'image/png')
  return <><canvas className="signature-canvas" ref={canvasRef} width="900" height="280" onPointerDown={start} onPointerMove={move} onPointerUp={() => { drawing.current = false }} /><div className="dialog-actions"><button className="secondary-button" onClick={() => canvasRef.current?.getContext('2d')?.clearRect(0, 0, 900, 280)}><Eraser size={16} /> Temizle</button><button className="primary-button" onClick={save}><PenLine size={16} /> İmzayı kullan</button></div></>
}
