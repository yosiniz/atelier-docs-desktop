import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { App } from './App'

test('ana çalışma araçlarını gösterir', () => {
  render(<MemoryRouter initialEntries={['/']}><App /></MemoryRouter>)
  expect(screen.getByText('Ne yapmak istersiniz?')).toBeInTheDocument()
  expect(screen.getByText('PDF Düzenle')).toBeInTheDocument()
  expect(screen.getByText('Görsel Düzenle')).toBeInTheDocument()
  expect(screen.getByText('Office Araçları').closest('button')).toBeEnabled()
  expect(screen.getByText('Toplu Görsel')).toBeInTheDocument()
  expect(screen.queryByText('Yakında')).not.toBeInTheDocument()
})
