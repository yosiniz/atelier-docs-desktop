import { useEffect, useRef, useState } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { HomePage } from './pages/HomePage'
import { ImageEditorPage } from './pages/ImageEditorPage'
import { PdfEditorPage } from './pages/PdfEditorPage'
import { OfficeEditorPage } from './pages/OfficeEditorPage'
import { useAppStore } from './store'
import { Toast } from './components/Toast'

export function App() {
  const theme = useAppStore((state) => state.theme)
  const navigate = useNavigate()
  const navigateRef = useRef(navigate)
  navigateRef.current = navigate
  const setDocument = useAppStore((state) => state.setDocument)
  const [openError, setOpenError] = useState<string | null>(null)
  useEffect(() => document.documentElement.setAttribute('data-theme', theme), [theme])
  useEffect(() => {
    const desktop = window.desktop
    if (!desktop?.takeOpenFile || !desktop.onOpenFiles) return
    let stopped = false
    let opening = false
    let rerun = false
    const openFiles = async () => {
      if (stopped) return
      if (opening) { rerun = true; return }
      opening = true
      try {
        while (!stopped) {
          let opened
          try { opened = await desktop.takeOpenFile() }
          catch (error) { setOpenError(error instanceof Error ? error.message : 'Dosya açılamadı'); continue }
          if (!opened || stopped) break
          setDocument(opened)
          navigateRef.current(opened.kind === 'pdf' ? '/pdf' : opened.kind === 'image' ? '/image' : '/office')
        }
      } finally { opening = false; if (rerun) { rerun = false; queueMicrotask(() => { void openFiles() }) } }
    }
    const unsubscribe = desktop.onOpenFiles(() => { void openFiles() })
    queueMicrotask(() => { if (!stopped) void openFiles() })
    return () => { stopped = true; unsubscribe() }
  }, [setDocument])
  return (
    <>
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/pdf" element={<PdfEditorPage />} />
      <Route path="/image" element={<ImageEditorPage />} />
      <Route path="/office" element={<OfficeEditorPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    {openError && <Toast message={openError} kind="error" onClose={() => setOpenError(null)} />}
    </>
  )
}
