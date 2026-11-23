import { StrictMode } from 'react'
import { act, cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { App } from './App'
import { useAppStore } from './store'

vi.mock('./pages/PdfEditorPage', () => ({ PdfEditorPage: () => <div>PDF dosyası açıldı</div> }))
vi.mock('./pages/ImageEditorPage', () => ({ ImageEditorPage: () => <div>Görsel dosyası açıldı</div> }))
vi.mock('./pages/OfficeEditorPage', () => ({ OfficeEditorPage: () => <div>Office dosyası açıldı</div> }))

afterEach(() => { cleanup(); delete window.desktop; useAppStore.getState().setDocument(null) })

test('cold-start Open With opens the document once under StrictMode', async () => {
  const file = { id: 'test-pdf', name: 'Türkçe dosya.pdf', kind: 'pdf', size: 123 }
  const take = vi.fn().mockResolvedValueOnce(file).mockResolvedValue(null)
  Object.defineProperty(window, 'desktop', { configurable: true, value: {
    takeOpenFile: take, onOpenFiles: () => () => {},
  } })
  render(<StrictMode><MemoryRouter><App /></MemoryRouter></StrictMode>)
  await screen.findByText('PDF dosyası açıldı')
  expect(useAppStore.getState().document?.name).toBe(file.name)
  expect(take).toHaveBeenCalledTimes(2)
})

test('an already running app receives a second Open With document', async () => {
  let notify = () => {}
  const take = vi.fn().mockResolvedValue(null)
  Object.defineProperty(window, 'desktop', { configurable: true, value: {
    takeOpenFile: take, onOpenFiles: (callback: () => void) => { notify = callback; return () => {} },
  } })
  render(<MemoryRouter><App /></MemoryRouter>)
  await waitFor(() => expect(take).toHaveBeenCalled())
  take.mockResolvedValueOnce({ id: 'image', name: 'test.png', kind: 'image', size: 100 }).mockResolvedValue(null)
  act(() => notify())
  await screen.findByText('Görsel dosyası açıldı')
  expect(useAppStore.getState().document?.name).toBe('test.png')
})
