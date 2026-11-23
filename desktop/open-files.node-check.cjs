const { test } = require('node:test')
const assert = require('node:assert/strict')
const path = require('node:path')
const { filesFromArguments } = require('./open-files.cjs')

test('Windows Open With accepts quoted-by-shell Unicode paths and ignores switches', () => {
  const file = path.resolve('tmp', 'Türkçe belge 2026.PDF')
  assert.deepEqual(filesFromArguments(['app.exe', '--inspect', '--smoke-test', file, file, path.resolve('app.cjs')]), [file])
})

test('all supported editor formats are accepted; relative paths and executables are ignored', () => {
  const files = ['a.pdf', 'a.png', 'a.docx', 'a.xlsx', 'a.pptx', 'a.csv'].map((name) => path.resolve('tmp', name))
  assert.deepEqual(filesFromArguments([...files, 'relative.pdf', path.resolve('unknown.exe')]), files)
})
