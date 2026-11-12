const { app, BrowserWindow, ipcMain, Menu, net, protocol, session } = require('electron')
const { resolve, dirname, sep } = require('node:path')
const { pathToFileURL } = require('node:url')

const origin = 'snap://studio'
const outputTitle = 'SNAP//REALITY — OBS OUTPUT'
const root = resolve(dirname(__dirname), 'dist')
let output
let control
let state = null
let sequence = 0

protocol.registerSchemesAsPrivileged([{
  scheme: 'snap',
  privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true, stream: true },
}])

function windowFor(role, options) {
  const win = new BrowserWindow({
    ...options,
    show: false,
    backgroundColor: '#000000',
    webPreferences: {
      preload: resolve(__dirname, 'preload.cjs'),
      additionalArguments: [`--snap-${role}`],
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      backgroundThrottling: role !== 'output',
    },
  })
  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
  win.webContents.on('will-navigate', event => event.preventDefault())
  win.on('page-title-updated', event => event.preventDefault())
  win.once('ready-to-show', () => win.show())
  win.loadURL(origin + '/index.html').catch(error => console.error('Could not load the studio:', error))
  return win
}

function showControl() {
  if (control && !control.isDestroyed()) {
    control.show()
    control.focus()
    return
  }
  control = windowFor('control', { width: 760, height: 770, minWidth: 520, minHeight: 550, title: 'SNAP//REALITY' })
  control.on('closed', () => { control = null })
}

function createWindows() {
  output = windowFor('output', { width: 1280, height: 720, useContentSize: true, title: outputTitle })
  output.setAspectRatio(16 / 9)
  output.on('closed', () => {
    output = null
    state = { ready: false, playable: false, available: false, camera: 'demo', devices: [], status: 'Output closed. Restart SNAP//REALITY to reopen it.' }
    control?.webContents.send('snap:state', state)
  })
  showControl()
}

function from(event, win) {
  return !!win && !win.isDestroyed() && event.sender === win.webContents &&
    event.senderFrame === win.webContents.mainFrame && event.senderFrame.url === origin + '/index.html'
}

function accepted(command) {
  if (!command || typeof command !== 'object') return false
  switch (command.action) {
    case 'start': return typeof command.device === 'string' && command.device.length <= 256
    case 'stop': case 'next': case 'previous': return true
    case 'effect': return Number.isInteger(command.value) && command.value >= 0 && command.value <= 20
    case 'profile': return [0, 1, 2].includes(command.level) && typeof command.locked === 'boolean'
    case 'strength': case 'amount': case 'sensitivity': return Number.isFinite(command.value) && command.value >= 0 && command.value <= 1
    case 'mirror': case 'cover': case 'tracking': case 'transition': return typeof command.value === 'boolean'
    default: return false
  }
}

app.whenReady().then(() => {
  Menu.setApplicationMenu(null)
  protocol.handle('snap', async request => {
    const url = new URL(request.url)
    if (url.hostname !== 'studio' || request.method !== 'GET') return new Response(null, { status: 404 })
    const decoded = decodeURIComponent(url.pathname)
    const target = resolve(root, '.' + decoded)
    if (!target.startsWith(root + sep)) return new Response(null, { status: 404 })
    const response = await net.fetch(pathToFileURL(target).href).catch(() => new Response(null, { status: 404 }))
    const headers = new Headers(response.headers)
    headers.set('Content-Security-Policy', "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; worker-src 'self'; style-src 'self'; img-src 'self' data: blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
    return new Response(response.body, { status: response.status, headers })
  })
  const localOutput = (contents, url) => !!output && !output.isDestroyed() &&
    contents === output.webContents && (url === origin || url === origin + '/' || url === origin + '/index.html')
  session.defaultSession.setPermissionCheckHandler((contents, permission, requestingOrigin, details) =>
    localOutput(contents, requestingOrigin) && permission === 'media' && details.mediaType === 'video')
  session.defaultSession.setPermissionRequestHandler((contents, permission, callback, details) => {
    callback(localOutput(contents, details.requestingUrl) && permission === 'media' &&
      details.isMainFrame && details.mediaTypes?.length === 1 && details.mediaTypes[0] === 'video')
  })
  ipcMain.on('snap:publish', (event, payload) => {
    if (!from(event, output)) return
    state = payload
    control?.webContents.send('snap:state', state)
  })
  ipcMain.handle('snap:command', (event, command) => {
    if (!from(event, control) || !output || !accepted(command)) return false
    const mediaCommand = command.action === 'start' || command.action === 'stop'
    if (!(mediaCommand ? state?.playable : state?.ready)) return false
    output.webContents.send('snap:apply', command, ++sequence)
    return true
  })
  ipcMain.handle('snap:read', event => from(event, control) ? state : null)
  ipcMain.handle('snap:controls', event => { if (from(event, output)) showControl() })
  ipcMain.handle('snap:show', event => {
    if (from(event, control) && output) { output.show(); output.focus() }
  })
  createWindows()
})

app.on('window-all-closed', () => app.quit())
