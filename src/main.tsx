import { createRoot } from 'react-dom/client'
import { App } from './App'
import { DesktopControl, DesktopOutput } from './Desktop'
import './style.css'

const role = window.snapDesktop?.role
createRoot(document.getElementById('root')!).render(role === 'output' ? <DesktopOutput />
  : role === 'control' ? <DesktopControl /> : <App />)
