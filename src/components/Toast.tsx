import { AlertCircle, CheckCircle2, X } from 'lucide-react'

export function Toast({ message, kind = 'success', onClose }: { message: string; kind?: 'success' | 'error'; onClose: () => void }) {
  return <div className={`toast ${kind}`}>
    {kind === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
    <span>{message}</span><button onClick={onClose} aria-label="Bildirimi kapat"><X size={16} /></button>
  </div>
}
