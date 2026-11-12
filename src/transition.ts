export const transitions = [
  'Off', 'Golden portal', 'Comic slam', 'Ink wipe', 'Neon shockwave', 'RGB tear',
  'Radial impact', 'Fracture reveal', 'Manga slashes', 'Halftone burst', 'Grid pull',
] as const

export type TransitionSettings = { style: number; duration: number; strength: number; reducedFlash: boolean; eased: boolean }
export const defaultTransition: TransitionSettings = { style: -1, duration: 240, strength: .7, reducedFlash: true, eased: true }
