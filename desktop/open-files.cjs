const fs = require('node:fs')
const path = require('node:path')

const supportedExtensions = new Set(['.pdf', '.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff', '.gif', '.docx', '.xlsx', '.pptx', '.csv'])

function filesFromArguments(args) {
  return [...new Set(args.filter((value) => typeof value === 'string' && path.isAbsolute(value)
    && supportedExtensions.has(path.extname(value).toLowerCase())))]
}

async function uploadLocalFile(filePath, apiBase, apiToken) {
  if (!path.isAbsolute(filePath) || !supportedExtensions.has(path.extname(filePath).toLowerCase())) {
    throw new Error('Bu dosya türü desteklenmiyor.')
  }
  const info = await fs.promises.stat(filePath)
  if (!info.isFile()) throw new Error('Seçilen yol bir dosya değil.')
  if (info.size > 250 * 1024 * 1024) throw new Error('Dosya 250 MB sınırını aşıyor.')
  const form = new FormData()
  form.append('file', await fs.openAsBlob(filePath), path.basename(filePath))
  const response = await fetch(`${apiBase}/files`, {
    method: 'POST', headers: apiToken ? { 'X-Atelier-Token': apiToken } : {}, body: form,
  })
  const body = await response.json()
  if (!response.ok) throw new Error(body.detail || 'Dosya açılamadı.')
  return body.data
}

module.exports = { filesFromArguments, uploadLocalFile }
