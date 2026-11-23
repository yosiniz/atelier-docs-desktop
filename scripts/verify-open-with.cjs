const assert = require('node:assert/strict')
const path = require('node:path')
const fs = require('node:fs')
const net = require('node:net')
const { spawn, spawnSync } = require('node:child_process')
const { uploadLocalFile } = require('../desktop/open-files.cjs')

async function verify() {
  const installed = path.join(process.env.LOCALAPPDATA, 'Programs', 'Atelier Docs')
  const extensions = ['pdf', 'png', 'jpg', 'jpeg', 'webp', 'bmp', 'tif', 'tiff', 'gif', 'docx', 'xlsx', 'pptx', 'csv']
  for (const extension of extensions) {
    const registry = spawnSync('reg.exe', ['query', `HKCU\\Software\\Classes\\.${extension}\\OpenWithProgids`, '/v', `AtelierDocs.${extension}`], { windowsHide: true, encoding: 'utf8' })
    assert.equal(registry.status, 0, `${extension} Open With registration missing`)
  }
  const command = spawnSync('reg.exe', ['query', 'HKCU\\Software\\Classes\\AtelierDocs.pdf\\shell\\open\\command', '/ve'], { windowsHide: true, encoding: 'utf8' })
  assert.equal(command.status, 0)
  assert(command.stdout.includes('Atelier Docs.exe" "%1"'), 'Filename must be individually quoted')

  const port = await new Promise((resolve) => {
    const server = net.createServer()
    server.listen(0, '127.0.0.1', () => { const value = server.address().port; server.close(() => resolve(value)) })
  })
  const token = require('node:crypto').randomBytes(24).toString('hex')
  const backend = spawn(path.join(installed, 'resources', 'backend', 'atelier-backend.exe'), [], {
    windowsHide: true, stdio: 'ignore', env: { ...process.env, ATELIER_PORT: String(port), ATELIER_API_TOKEN: token },
  })
  try {
    const base = `http://127.0.0.1:${port}/api`
    let ready = false
    for (let attempt = 0; attempt < 100; attempt += 1) {
      try { if ((await fetch(`${base}/health`)).ok) { ready = true; break } } catch { /* starting */ }
      await new Promise((resolve) => setTimeout(resolve, 250))
    }
    assert(ready, 'Backend did not start')
    const fixture = path.resolve('output/pdf/ocr-quality-source.pdf')
    assert(fs.existsSync(fixture), 'Local OCR fixture is required')
    const opened = await uploadLocalFile(fixture, base, token)
    assert.equal(opened.kind, 'pdf')
    assert.equal(opened.name, path.basename(fixture))
    assert(opened.pdf.page_count > 0)
    console.log(JSON.stringify({ openWithRegistry: 'passed', supportedTypes: extensions.length, quotedFileCommand: 'passed', nativeFileUpload: 'passed' }))
  } finally {
    spawnSync('taskkill.exe', ['/pid', String(backend.pid), '/t', '/f'], { windowsHide: true, stdio: 'ignore' })
  }
}
verify().catch((error) => { console.error(error.message); process.exitCode = 1 })
