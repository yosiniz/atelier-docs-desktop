const { app, BrowserWindow, dialog, ipcMain, shell } = require('electron')
const path = require('node:path')
const fs = require('node:fs')
const net = require('node:net')
const crypto = require('node:crypto')
const { spawn, spawnSync } = require('node:child_process')

const isDev = !app.isPackaged
const smokeMode = process.argv.includes('--smoke-test')
let backendProcess = null
let apiPort = 8765
let apiToken = ''

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.unref()
    server.on('error', reject)
    server.listen(0, '127.0.0.1', () => {
      const address = server.address()
      const port = typeof address === 'object' && address ? address.port : 8765
      server.close(() => resolve(port))
    })
  })
}

async function waitForBackend(port, token) {
  const deadline = Date.now() + 30000
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/api/health`, {
        headers: token ? { 'X-Atelier-Token': token } : {},
      })
      if (response.ok) return
    } catch { /* backend is still starting */ }
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  throw new Error('Yerel belge motoru 30 saniye içinde başlatılamadı.')
}

async function startPackagedBackend() {
  if (isDev) return
  apiPort = await freePort()
  apiToken = crypto.randomBytes(32).toString('hex')
  const executableName = process.platform === 'win32' ? 'atelier-backend.exe' : 'atelier-backend'
  const executable = path.join(process.resourcesPath, 'backend', executableName)
  if (!fs.existsSync(executable)) {
    throw new Error(`Yerel belge motoru bulunamadı: ${executableName}`)
  }
  backendProcess = spawn(executable, [], {
    windowsHide: true,
    stdio: 'ignore',
    env: { ...process.env, ATELIER_PORT: String(apiPort), ATELIER_API_TOKEN: apiToken },
  })
  backendProcess.on('exit', () => { backendProcess = null })
  await waitForBackend(apiPort, apiToken)
}

function createWindow() {
  const window = new BrowserWindow({
    width: 1500,
    height: 940,
    minWidth: 1080,
    minHeight: 700,
    backgroundColor: '#10120f',
    titleBarStyle: 'hiddenInset',
    show: !smokeMode,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      additionalArguments: [`--atelier-api-port=${apiPort}`, `--atelier-api-token=${apiToken}`],
    },
  })

  if (smokeMode) {
    const output = process.env.ATELIER_SMOKE_OUTPUT || path.join(app.getPath('temp'), 'atelier-docs-smoke.json')
    let finished = false
    const complete = (result, exitCode) => {
      if (finished) return
      finished = true
      fs.writeFileSync(output, JSON.stringify(result, null, 2), 'utf8')
      process.exitCode = exitCode
      app.quit()
    }
    const timeout = setTimeout(() => complete({ ok: false, error: 'Renderer zaman aşımı' }, 2), 45000)
    window.webContents.once('did-fail-load', (_event, code, description, url) => {
      clearTimeout(timeout)
      complete({ ok: false, code, description, url }, 2)
    })
    window.webContents.once('did-finish-load', async () => {
      try {
        const state = await window.webContents.executeJavaScript(`({
          title: document.title,
          rootChildren: document.getElementById('root')?.children.length || 0,
          textLength: document.body?.innerText?.length || 0
        })`)
        clearTimeout(timeout)
        complete({ ok: state.rootChildren > 0 && state.textLength > 0, ...state }, state.rootChildren > 0 && state.textLength > 0 ? 0 : 2)
      } catch (error) {
        clearTimeout(timeout)
        complete({ ok: false, error: error instanceof Error ? error.message : String(error) }, 2)
      }
    })
  }

  if (isDev) window.loadURL('http://127.0.0.1:5173')
  else window.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
}

ipcMain.handle('dialog:save', async (_event, options) => dialog.showSaveDialog(options))
ipcMain.handle('file:write', async (_event, targetPath, bytes) => {
  const data = Buffer.from(bytes)
  await fs.promises.writeFile(targetPath, data)
  return { ok: true, size: data.byteLength }
})
ipcMain.handle('shell:show-item', (_event, targetPath) => shell.showItemInFolder(targetPath))

app.whenReady().then(async () => {
  try {
    await startPackagedBackend()
  } catch (error) {
    dialog.showErrorBox('Atelier Docs başlatılamadı', error instanceof Error ? error.message : String(error))
    app.quit()
    return
  }
  createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', () => {
  if (backendProcess) {
    if (process.platform === 'win32') {
      spawnSync('taskkill', ['/pid', String(backendProcess.pid), '/t', '/f'], { windowsHide: true, stdio: 'ignore' })
    } else {
      backendProcess.kill('SIGTERM')
    }
    backendProcess = null
  }
})
