const { contextBridge, ipcRenderer } = require('electron')

const portArg = process.argv.find((value) => value.startsWith('--atelier-api-port='))
const tokenArg = process.argv.find((value) => value.startsWith('--atelier-api-token='))
const apiPort = portArg ? portArg.split('=')[1] : '8765'
const apiToken = tokenArg ? tokenArg.slice(tokenArg.indexOf('=') + 1) : ''

contextBridge.exposeInMainWorld('desktop', {
  saveDialog: (options) => ipcRenderer.invoke('dialog:save', options),
  writeFile: (targetPath, bytes) => ipcRenderer.invoke('file:write', targetPath, bytes),
  showItemInFolder: (targetPath) => ipcRenderer.invoke('shell:show-item', targetPath),
  platform: process.platform,
  apiBase: `http://127.0.0.1:${apiPort}/api`,
  apiToken,
})
