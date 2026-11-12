export const effects = [
  { id: 0, label: 'Original', control: '' },
  { id: 1, label: '2D / 3D Style', control: 'Illustration blend' },
  { id: 2, label: 'Comic Book', control: 'Ink weight' },
  { id: 3, label: 'Halftone Print', control: 'Dot pitch' },
  { id: 4, label: 'Cel Shading', control: 'Shadow bands' },
  { id: 5, label: 'Posterization', control: 'Color levels' },
  { id: 6, label: 'Kinetic Typography', control: 'Title size' },
  { id: 7, label: 'Speed Lines', control: 'Line density' },
  { id: 8, label: 'Radial Zoom Blur', control: 'Zoom depth' },
  { id: 9, label: 'RGB Glitch', control: 'Channel separation' },
  { id: 10, label: 'Frame Echo', control: 'Echo decay' },
  { id: 11, label: 'Ink Splash', control: 'Ink coverage' },
  { id: 12, label: 'Impact Frame', control: 'Duotone contrast' },
  { id: 13, label: 'Prismatic Fracture', control: 'Refraction' },
  { id: 14, label: 'Geometric Shatter', control: 'Piece displacement' },
  { id: 15, label: 'Neon Energy Trails', control: 'Glow radius' },
  { id: 16, label: 'Color Remapping', control: 'Palette bias' },
  { id: 17, label: 'Vortex Portal', control: 'Swirl' },
  { id: 18, label: 'Synthwave Grid', control: 'Grid depth' },
  { id: 19, label: 'Comic Starburst', control: 'Ray count' },
  { id: 20, label: 'Mixed Media', control: 'Layer mix' },
] as const

export const vertex = `
varying vec2 point;
void main() {
  point = uv;
  gl_Position = vec4(position.xy, 0., 1.);
}
`

const sourceShader = `
varying vec2 point;
uniform sampler2D live;
uniform sampler2D titleMap;
uniform sampler2D recentFrame;
uniform sampler2D olderFrame;
uniform bool demo;
uniform bool mirrored;
uniform float historyCount;
uniform vec2 fit;
uniform vec2 size;
uniform int effect;
uniform float time;
uniform float strength;
uniform float amount;
uniform float impact;
uniform int detailLevel;
float sourceLuma(vec3 c) { return dot(c, vec3(.2126, .7152, .0722)); }
float noise(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
vec3 sampleSource(vec2 p) {
  if (!demo) {
    vec2 q = (p - .5) * fit + .5;
    if (mirrored) q.x = 1. - q.x;
    if (any(lessThan(q, vec2(0.))) || any(greaterThan(q, vec2(1.)))) return vec3(0.);
    return texture2D(live, q).rgb;
  }
  vec2 q = (p - .5) * vec2(1.78, 1.);
  vec3 c = mix(vec3(.035,.07,.16), vec3(.28,.09,.31), p.y);
  vec2 tiles = abs(fract((q + vec2(time * .11, time * -.035)) * 6.) - .5);
  c += vec3(.1,.28,.34) * step(.47, max(tiles.x, tiles.y));
  float sun = length(q - vec2(.28 * sin(time * .85), .12 * cos(time)));
  c = mix(c, mix(vec3(1.,.23,.17),vec3(1.,.8,.39),p.y), 1. - smoothstep(.219,.223,sun));
  float hill = -.29 + .08 * sin(12. * q.x + time) + .07 * sin(7. * q.x - time * .5);
  return mix(c, mix(vec3(.09,.14,.25), vec3(.12,.58,.58), p.y), 1. - smoothstep(hill,hill+.007,q.y));
}
`

export const previewFragment = sourceShader + `
void main() { gl_FragColor = vec4(sampleSource(point), 1.); }
`

export const fragment = sourceShader + `
float edgeAt(vec2 p, float center, float pixels) {
  vec2 d = pixels / size;
  float x = abs(sourceLuma(sampleSource(p + vec2(d.x, 0.))) - center);
  float y = abs(sourceLuma(sampleSource(p + vec2(0., d.y))) - center);
  return smoothstep(.025, .13, x + y);
}
vec2 rotatePoint(vec2 p, float angle) {
  float s = sin(angle);
  float c = cos(angle);
  return mat2(c, s, -s, c) * p;
}
float screenAngle(vec2 p) { return atan(p.y, p.x + .00001); }
float halftoneAt(vec2 p, float y, float pitch) {
  vec2 grid = rotatePoint(p * size, .52);
  float radius = sqrt(1. - clamp(y, 0., 1.)) * .53;
  return smoothstep(radius, radius + .075, length(fract(grid / pitch) - .5));
}
vec3 comicAt(vec2 p, vec3 c, float y, float weight) {
  vec3 ink = floor(clamp(mix(vec3(y), c, 1.35), 0., 1.) * 5. + .5) / 5.;
  return mix(ink * .8 + vec3(.12,.04,.07), vec3(.018,.01,.04), edgeAt(p, y, weight));
}
float titleAt(vec2 p, float scale, float y, float angle) {
  vec2 q = rotatePoint((p - vec2(.5,y)) * vec2(1.7778, 1.), angle) / vec2(scale, scale * .28) + .5;
  if (any(lessThan(q, vec2(0.))) || any(greaterThan(q, vec2(1.)))) return 0.;
  return texture2D(titleMap, q).a;
}
vec3 delayedColor(vec2 p, vec3 c, float decay) {
  vec3 recent = historyCount > 0. ? texture2D(recentFrame, clamp(p + vec2(.022,0.),0.,1.)).rgb : sampleSource(p + vec2(.022,0.));
  vec3 older = historyCount > 1. ? texture2D(olderFrame, clamp(p - vec2(.027,0.),0.,1.)).rgb : sampleSource(p - vec2(.027,0.));
  return c * (1. - decay * .45) + recent * vec3(.85,.42,.7) * decay + older * vec3(.12,.63,.8) * decay;
}
vec3 applyEffect(int mode, vec2 p, vec3 c, float param) {
  float y = sourceLuma(c);
  vec2 centered = (p - .5) * vec2(1.7778, 1.);
  float radius = length(centered);
  if (mode == 1) {
    vec3 graded = (c * c * 1.4 + vec3(.12,.07,.035)) * (1. - .65 * smoothstep(.14,.8,radius));
    graded += (noise(floor(p * size) + floor(time * 18.)) - .5) * .05;
    return mix(graded, comicAt(p,c,y,1.3), param);
  }
  if (mode == 2) return comicAt(p,c,y,1. + param * 2.);
  if (mode == 3) return mix(vec3(.025,.05,.12), vec3(.98,.9,.73), halftoneAt(p, y, 4. + param * 8.));
  if (mode == 4) {
    float bands = floor(mix(2., 9., param));
    float shade = floor(y * bands + .35) / bands;
    return mix(vec3(.035,.08,.16) + c * (.38 + 1.5 * shade), vec3(.01,.035,.08), edgeAt(p,y,1.1) * .73);
  }
  if (mode == 5) {
    float levels = floor(2. + param * 4. + .5);
    return floor(clamp(c + (noise(floor(p * size)) - .5) * .075, 0., 1.) * levels + .5) / levels;
  }
  if (mode == 6) {
    float pulse = pow(max(0., sin(time * 3.2)), 5.);
    float scale = .45 + .65 * param + .15 * pulse;
    float letters = titleAt(p, scale, .27 + pulse * .07, -.16);
    float shadow = titleAt(p - vec2(.008,.014), scale, .27 + pulse * .07, -.16);
    float band = 1. - smoothstep(.062,.067,abs(p.y - .23 - p.x * .12));
    return mix(mix(c, c * .35 + vec3(.17,.04,.28), band * .8), vec3(.94,.97,.55), letters)
      + vec3(.1,.04,.34) * max(0., shadow - letters);
  }
  if (mode == 7) {
    float angle = screenAngle(centered);
    float ray = (angle + 3.142) * mix(18., 59., param);
    float line = smoothstep(.8,.98,fract(ray));
    float motion = smoothstep(.35,.7,fract(radius * 1.9 + time * 1.65 + noise(vec2(floor(ray),1.))));
    return mix(c, vec3(.86,.93,1.), line * motion * smoothstep(.22,.68,radius) * .86);
  }
  if (mode == 8) {
    vec3 blur = c;
    float weights = 1.;
    for (int i = 1; i <= 8; i++) {
      if (detailLevel == 0 && i > 4) break;
      float weight = 1. - float(i) * .085;
      blur += sampleSource(p - (p - .5) * (param + .15) * float(i) * .075) * weight;
      weights += weight;
    }
    return blur / weights;
  }
  if (mode == 9) {
    float band = noise(vec2(floor(p.y * 28.), floor(time * 12.)));
    vec2 offset = vec2(.003 + param * .01 + step(.87, band) * .035, 0.);
    return vec3(sampleSource(p + offset).r, c.g, sampleSource(p - offset).b) * (.91 + .09 * sin(p.y * size.y * 1.57));
  }
  if (mode == 10) return delayedColor(p,c,.18 + param * .66);
  if (mode == 11) {
    vec2 brush = rotatePoint(centered, -.62);
    float grain = noise(floor(brush * vec2(120.,28.)));
    float splash = abs(brush.y + .12 * sin(brush.x * 12. + time)) + .12 * grain;
    float ink = 1. - smoothstep(.12 + .22 * param, .18 + .22 * param, splash);
    return mix(c * vec3(.95,.86,.8), vec3(.013,.009,.023), ink * .88);
  }
  if (mode == 12) {
    float b = smoothstep(.1 + .25 * param, .95 - .25 * param, y);
    return mix(vec3(.02,.01,.05), vec3(1.,.95,.72), b) * (.88 + .12 * sin(time * 1.9 + radius));
  }
  if (mode == 13) {
    vec2 uv = rotatePoint(centered, .36) * 12.;
    vec2 cell = floor(uv);
    vec2 shard = fract(uv);
    float side = step(1., shard.x + shard.y);
    float seed = noise(cell + side * .43);
    vec2 offset = vec2(sin(seed * 6.28), cos(seed * 6.28)) * (.01 + .11 * param) * (.75 + .25 * sin(time * 2. + seed * 10.));
    vec3 refracted = vec3(sampleSource(p + offset * 1.12).r, sampleSource(p + offset).g, sampleSource(p + offset * .82).b);
    float rim = 1. - smoothstep(.012,.045,abs(shard.x + shard.y - 1.));
    return refracted + vec3(.18,.34,.55) * rim;
  }
  if (mode == 14) {
    vec2 tiles = vec2(10.,6.);
    vec2 cell = floor(p * tiles);
    vec2 local = fract(p * tiles) - .5;
    float seed = noise(cell);
    float shift = (.14 + param * .4) * (.55 + .45 * sin(time * 2.4 + seed * 5.));
    vec2 piece = rotatePoint(local - (seed - .5) * shift, shift * (seed - .5) * 2.);
    float visible = 1. - smoothstep(.43,.48,max(abs(piece.x),abs(piece.y)));
    return mix(c * .17, sampleSource((cell + .5 + piece / (1. + shift * .3)) / tiles), visible);
  }
  if (mode == 15) {
    float glow = edgeAt(p, y, 1.5 + param * 6.);
    float core = edgeAt(p, y, 1.5);
    return c * .41 + vec3(.02,.87,.72) * glow * .65 + vec3(.78,.16,.9) * core * .65 + delayedColor(p,c,.4) * .28;
  }
  if (mode == 16) {
    vec3 middle = mix(vec3(.65,.2,.73), vec3(1.09,-.16,.29), param);
    return mix(mix(vec3(.04,.01,.18), middle, smoothstep(0.,.54,y)), vec3(.38,1.,.84), smoothstep(.45,1.,y));
  }
  if (mode == 17) {
    float border = .32 + .024 * sin(time * 2.8);
    float swirl = (1. - smoothstep(0.,border,radius)) * (1. + param * 7.);
    vec2 q = rotatePoint(centered, swirl) / vec2(1.7778,1.) + .5;
    float rim = 1. - smoothstep(.008,.05,abs(radius - border));
    float rings = .5 + .5 * sin(radius * 112. - time * 7.);
    return sampleSource(q) + vec3(.64,.26,.08) * (rim * .8 + rings * .13 * (1. - smoothstep(border,border+.12,radius)));
  }
  if (mode == 18) {
    float horizon = .41;
    float z = max(.025,horizon - p.y);
    vec2 grid = vec2(centered.x * (1.7 + param * 4.) / z, 1.25 / z + time * 1.9);
    vec2 lines = abs(fract(grid) - .5);
    float g = smoothstep(.43,.49,max(lines.x,lines.y)) * (1. - smoothstep(.04,.16,abs(p.y - .25))) * step(p.y,horizon);
    return mix(c, c * vec3(.74,.38,.96) + vec3(.16,.02,.21), .53)
      + vec3(.83,.06,.69) * g * .6 + vec3(.24,.03,.25) * exp(-abs(p.y - horizon) * 24.);
  }
  if (mode == 19) {
    float angle = screenAngle(centered) + time * .31;
    float zigzag = abs(fract(angle * mix(1.8,5.7,param)) - .5) * .78;
    float tip = .38 + zigzag + .035 * sin(time * 4.);
    float border = 1. - smoothstep(.018,.028,abs(tip - radius));
    float field = smoothstep(tip,tip+.02,radius);
    return mix(c, vec3(.94,.61,.09) * (.8 + y * .35), field * .86) * (1. - border * .85);
  }
  if (mode == 20) {
    vec3 ink = comicAt(p,c,y,2.);
    vec3 dots = mix(vec3(.08,.025,.18), c * .6 + vec3(.16,.43,.43), halftoneAt(p,y,6.));
    float pane = smoothstep(-.06,.06,centered.x + centered.y * .46 - .12 * sin(time * .8));
    float text = titleAt(p,.64,.31,-.1);
    return mix(mix(dots, ink, mix(.1,.9,pane) * (.6 + .4 * param)), vec3(.96,.83,.36), text * .82);
  }
  return c;
}
void main() {
  vec2 p = point;
  vec3 c = sampleSource(p);
  c = mix(c, applyEffect(effect, p, c, amount), strength);
  float ring = 1. - smoothstep(.012,.045,abs(length((p - .5) * vec2(1.78,1.)) - .8 * (1. - impact)));
  c += vec3(.18,.34,.32) * ring * impact;
  gl_FragColor = vec4(clamp(c, 0., 1.), 1.);
}
`
