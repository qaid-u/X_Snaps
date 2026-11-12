void main() {
    vec2 uv = vUV.st;
    vec4 source = sourceAt(uv);
    vec2 aspect = aspectScale();
    float scale = max(2.0, uParams.x);
    float t = uOptions.x * uParams.w;
    vec2 paperUV = (uv * aspect + vec2(t * 0.028, -t * 0.014)) * scale;
    vec2 tile = floor(paperUV);
    vec2 inside = fract(paperUV);
    float seed = hash21(tile + uOptions.y);
    float edges = min(min(inside.x, inside.y), min(1.0 - inside.x, 1.0 - inside.y));
    float seam = 1.0 - smoothstep(0.005, 0.019, edges);
    vec2 shift = (vec2(seed, hash21(tile + 27.1)) - 0.5) * 0.060 / aspect;
    vec3 cutout = sourceAt(uv + shift).rgb;
    vec3 poster = quantizeColor(cutout * vec3(1.17, 1.06, 0.95), max(2.0, uParams.y));
    float gradient = length(luminanceGradient(uv, 2.3));
    vec3 illustrated = mix(poster * 0.82 + vec3(0.11, 0.085, 0.17), vec3(0.055, 0.043, 0.092),
        smoothstep(0.063, 0.23, gradient));
    vec3 split = vec3(sourceAt(uv + shift + vec2(uParams.z, 0.0)).r, cutout.g,
        sourceAt(uv + shift - vec2(uParams.z, 0.0)).b);
    float newsprint = dotScreen(gl_FragCoord.xy, 8.0, 0.7, 0.66 * (1.0 - luma(cutout)));
    vec3 archive = mix(vec3(0.13, 0.17, 0.18), vec3(0.91, 0.89, 0.65), luma(cutout)) * (1.0 - 0.33 * newsprint);
    vec3 color = seed < 0.32 ? illustrated : (seed < 0.61 ? split : archive);
    writeEffect(source, mix(color, vec3(0.058, 0.049, 0.075), seam * 0.64));
}
