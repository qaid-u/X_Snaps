export const effects = [
  { id: 0, label: 'Original' },
  { id: 2, label: 'Comic Book' },
  { id: 3, label: 'Halftone Print' },
  { id: 5, label: 'Posterization' },
  { id: 9, label: 'RGB Glitch' },
  { id: 16, label: 'Color Remapping' },
] as const

export const vertex = `
varying vec2 point;
void main() {
  point = uv;
  gl_Position = vec4(position.xy, 0., 1.);
}
`

export const fragment = `
varying vec2 point;
uniform sampler2D live;
uniform bool demo;
uniform bool mirrored;
uniform vec2 fit;
uniform vec2 size;
uniform int effect;
uniform float time;
uniform float strength;
uniform float impact;
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
float edgeAt(vec2 p, float center) {
  vec2 d = 2. / size;
  float x = abs(sourceLuma(sampleSource(p + vec2(d.x, 0.))) - center);
  float y = abs(sourceLuma(sampleSource(p + vec2(0., d.y))) - center);
  return smoothstep(.025, .13, x + y);
}
void main() {
  vec2 p = point;
  vec3 c = sampleSource(p);
  float y = sourceLuma(c);
  vec3 styled = c;
  if (effect == 2) {
    vec3 ink = floor(clamp(mix(vec3(y), c, 1.35), 0., 1.) * 5. + .5) / 5.;
    styled = mix(ink * .8 + vec3(.12,.04,.07), vec3(.018,.01,.04), edgeAt(p, y));
  } else if (effect == 3) {
    vec2 grid = mat2(.87, .5, -.5, .87) * (p * size);
    float dotInk = smoothstep(sqrt(1. - y) * .53, sqrt(1. - y) * .53 + .075, length(fract(grid / 8.) - .5));
    styled = mix(vec3(.025,.05,.12), vec3(.98,.9,.73), dotInk);
  } else if (effect == 5) {
    styled = floor(clamp(c + (noise(floor(p * size)) - .5) * .075, 0., 1.) * 4. + .5) / 4.;
  } else if (effect == 9) {
    float band = noise(vec2(floor(p.y * 28.), floor(time * 12.)));
    vec2 offset = vec2(.008 + step(.87, band) * .035, 0.);
    styled = vec3(sampleSource(p + offset).r, c.g, sampleSource(p - offset).b);
    styled *= .91 + .09 * sin(p.y * size.y * 1.57);
  } else if (effect == 16) {
    styled = mix(mix(vec3(.04,.01,.18), vec3(.87,.02,.51), smoothstep(0.,.54,y)),
      vec3(.38,1.,.84), smoothstep(.45,1.,y));
  }
  c = mix(c, styled, strength);
  float ring = 1. - smoothstep(.012,.045,abs(length((p - .5) * vec2(1.78,1.)) - .8 * (1. - impact)));
  c += vec3(.18,.34,.32) * ring * impact;
  gl_FragColor = vec4(clamp(c, 0., 1.), 1.);
}
`
