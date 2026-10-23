import { useEffect } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { HomePage } from './pages/HomePage'
import { ImageEditorPage } from './pages/ImageEditorPage'
import { PdfEditorPage } from './pages/PdfEditorPage'
import { OfficeEditorPage } from './pages/OfficeEditorPage'
import { useAppStore } from './store'

export function App() {
  const theme = useAppStore((state) => state.theme)
  useEffect(() => document.documentElement.setAttribute('data-theme', theme), [theme])
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/pdf" element={<PdfEditorPage />} />
      <Route path="/image" element={<ImageEditorPage />} />
      <Route path="/office" element={<OfficeEditorPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
