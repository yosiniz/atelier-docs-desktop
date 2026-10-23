const { existsSync, readdirSync, unlinkSync } = require('node:fs')
const { join, resolve } = require('node:path')
const { spawn, spawnSync } = require('node:child_process')

const projectRoot = resolve(__dirname, '..')
const releaseDir = join(projectRoot, 'release')
const userInstall = join(process.env.LOCALAPPDATA || '', 'Programs', 'Atelier Docs')
const systemInstall = join(process.env.ProgramFiles || 'C:\\Program Files', 'Atelier Docs')

function versionOf(name) {
  const match = name.match(/^Atelier-Docs-(\d+\.\d+\.\d+)-Setup\.exe$/i)
  return match ? match[1].split('.').map(Number) : null
}

function compareVersions(left, right) {
  for (let index = 0; index < 3; index += 1) {
    if (left[index] !== right[index]) return left[index] - right[index]
  }
  return 0
}

function run(executable, args, label) {
  const result = spawnSync(executable, args, { windowsHide: true, stdio: 'inherit' })
  if (result.error) throw new Error(`${label}: ${result.error.message}`)
  if (result.status !== 0) throw new Error(`${label} başarısız oldu (kod ${result.status})`)
}

const installers = readdirSync(releaseDir)
  .map((name) => ({ name, version: versionOf(name) }))
  .filter((item) => item.version)
  .sort((left, right) => compareVersions(left.version, right.version))

if (!installers.length) throw new Error('Kurulacak Atelier Docs paketi bulunamadı')
const latest = installers.at(-1)
const installer = join(releaseDir, latest.name)

// Aynı kullanıcıdaki eski kurulum resmi NSIS kaldırıcıyla temizlenir.
const userUninstaller = join(userInstall, 'Uninstall Atelier Docs.exe')
if (existsSync(userUninstaller)) run(userUninstaller, ['/S'], 'Eski kullanıcı kurulumu kaldırılamadı')

// Önceki sistem-geneli kurulum kalmışsa yalnızca resmi kaldırıcı kullanılır.
const systemUninstaller = join(systemInstall, 'Uninstall Atelier Docs.exe')
if (existsSync(systemUninstaller)) run(systemUninstaller, ['/S'], 'Eski sistem kurulumu kaldırılamadı')

run(installer, ['/S', '/currentuser'], 'Yeni sürüm kurulamadı')

const installedExecutable = join(userInstall, 'Atelier Docs.exe')
if (!existsSync(installedExecutable)) throw new Error('Kurulum tamamlandı ancak uygulama bulunamadı')

const application = spawn(installedExecutable, [], { detached: true, windowsHide: false, stdio: 'ignore' })
application.unref()

// Kurulum doğrulandıktan sonra yalnızca güncel kurulum paketi ve blockmap tutulur.
for (const item of installers.slice(0, -1)) {
  const oldInstaller = join(releaseDir, item.name)
  const oldBlockMap = `${oldInstaller}.blockmap`
  if (existsSync(oldInstaller)) unlinkSync(oldInstaller)
  if (existsSync(oldBlockMap)) unlinkSync(oldBlockMap)
}
process.stdout.write(`Atelier Docs ${latest.version.join('.')} kuruldu ve başlatıldı.\n`)
