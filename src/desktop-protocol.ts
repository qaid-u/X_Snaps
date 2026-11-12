import type { Engine } from './Engine'

export type Command =
  | { action: 'start'; device: string }
  | { action: 'stop' | 'next' | 'previous' }
  | { action: 'effect' | 'strength' | 'sensitivity'; value: number }
  | { action: 'mirror' | 'cover' | 'tracking' | 'transition'; value: boolean }
  | { action: 'profile'; level: number; locked: boolean }

export type DesktopState = {
  ready: boolean
  camera: 'demo' | 'starting' | 'live'
  status: string
  devices: { id: string; label: string }[]
  metrics?: ReturnType<Engine['snapshot']>
  available: boolean
}

type OutputBridge = {
  role: 'output'
  onCommand(callback: (command: Command, seq: number) => void): () => void
  publish(state: DesktopState): void
  showControls(): Promise<void>
}

type ControlBridge = {
  role: 'control'
  command(command: Command): Promise<boolean>
  read(): Promise<DesktopState | null>
  onState(callback: (state: DesktopState) => void): () => void
  showOutput(): Promise<void>
}

declare global {
  interface Window { snapDesktop?: OutputBridge | ControlBridge }
}
