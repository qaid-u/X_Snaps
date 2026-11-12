const { contextBridge, ipcRenderer } = require('electron')

function listen(channel, callback) {
  const listener = (_event, ...args) => callback(...args)
  ipcRenderer.on(channel, listener)
  return () => ipcRenderer.removeListener(channel, listener)
}

if (process.argv.includes('--snap-output')) {
  contextBridge.exposeInMainWorld('snapDesktop', {
    role: 'output',
    onCommand: callback => listen('snap:apply', callback),
    publish: state => ipcRenderer.send('snap:publish', state),
    showControls: () => ipcRenderer.invoke('snap:controls'),
  })
} else {
  contextBridge.exposeInMainWorld('snapDesktop', {
    role: 'control',
    command: command => ipcRenderer.invoke('snap:command', command),
    read: () => ipcRenderer.invoke('snap:read'),
    onState: callback => listen('snap:state', callback),
    showOutput: () => ipcRenderer.invoke('snap:show'),
  })
}
