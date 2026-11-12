// TD pixel shader. Inputs: previous source, target source, optional type TOP.
uniform vec4 uTransition; // progress, strength, center X, center Y
uniform vec4 uLayers;     // wipe ID, flash amount, first and second overlay IDs
uniform vec4 uTiming;     // two overlay progresses, elapsed seconds, type progress

layout(location = 0) out vec4 fragColor;

const float TAU = 6.2831853;

float hashCell(vec2 cell)
{
    return fract(sin(dot(cell, vec2(127.1, 311.7))) * 43758.5453);
}

float valueNoise(vec2 p)
{
    vec2 cell = floor(p);
    vec2 t = fract(p);
    t = t * t * (3.0 - 2.0 * t);
    return mix(mix(hashCell(cell), hashCell(cell + vec2(1, 0)), t.x),
               mix(hashCell(cell + vec2(0, 1)), hashCell(cell + vec2(1, 1)), t.x), t.y);
}

float lineMask(float x, float width)
{
    float feather = max(fwidth(x), 0.003);
    return 1.0 - smoothstep(width, width + feather, abs(x));
}

vec2 safeUV(vec2 uv)
{
    return clamp(uv, vec2(0.0), vec2(1.0));
}

float wipeMask(int kind, vec2 uv, vec2 p, float progress, float aspect)
{
    if (progress <= 0.0 || progress >= 1.0)
        return progress;

    float threshold = progress;
    float field = 0.0;
    if (kind == 1) {
        field = length(p) / max(0.6, 1.12 * length(vec2(aspect, 1.0)));
    } else if (kind == 2) {
        field = clamp(uv.x * 0.75 + 0.21 * valueNoise(uv * vec2(8.0, 34.0))
                      + 0.04 * valueNoise(uv * vec2(32.0, 120.0)), 0.0, 1.0);
    } else if (kind == 3) {
        field = 0.60 * uv.x + 0.40 * hashCell(floor(uv * vec2(21.0, 12.0)));
    } else if (kind == 4) {
        field = clamp(0.72 * uv.x + 0.28 * (1.0 - uv.y), 0.0, 1.0);
    } else {
        return smoothstep(0.0, 1.0, progress);
    }

    return smoothstep(-0.06, 0.06, threshold * 1.12 - 0.06 - field);
}

vec3 blendOverlay(vec3 rgb, int id, float local, vec2 uv, vec2 p, float strength)
{
    if (id == 0 || local <= 0.0 || local >= 1.0)
        return rgb;

    float r = length(p);
    float angle = atan(p.y, p.x);
    float envelope = smoothstep(0.0, 0.13, local) * (1.0 - smoothstep(0.45, 1.0, local));
    float alpha = 0.0;
    vec3 ink = vec3(0.0);

    if (id == 1) { // NEON_BEAMS
        float sector = angle / TAU * 19.0;
        alpha = lineMask(fract(sector + 0.5) - 0.5, 0.055)
                * smoothstep(local * 0.45, local * 0.45 + 0.14, r);
        ink = mix(vec3(0.06, 0.96, 1.0), vec3(0.71, 1.0, 0.18), step(0.5, fract(sector * 0.55)));
    } else if (id == 2) { // EXPLOSION_BURST
        float ripple = 0.035 * sin(angle * 11.0) + 0.025 * sin(angle * 23.0);
        float radius = mix(0.03, 0.75, local);
        float edge = lineMask(r - radius - ripple, 0.019);
        float core = (1.0 - smoothstep(radius * 0.16, radius + ripple, r)) * 0.72;
        alpha = max(edge, core);
        ink = mix(vec3(1.0, 0.12, 0.035), vec3(1.0, 0.87, 0.28), core);
    } else if (id == 3) { // GOLDEN_SIGIL
        float scale = mix(0.62, 1.5, local);
        float ring = max(lineMask(r - 0.18 * scale, 0.0015), lineMask(r - 0.25 * scale, 0.0015));
        ring = max(ring, lineMask(r - 0.28 * scale, 0.002));
        float polygon = cos((fract((angle + local) * 6.0 / TAU) - 0.5) * TAU / 6.0) * r;
        alpha = max(ring, lineMask(polygon - 0.215 * scale, 0.002));
        ink = vec3(1.0, 0.75, 0.21);
    } else if (id == 4) { // SHARD_PORTAL
        float opening = abs(p.x) * 0.73 + abs(p.y);
        float edge = lineMask(opening - mix(0.055, 0.50, local), 0.007);
        float sector = angle * 13.0 / TAU;
        float shards = lineMask(fract(sector + r * 1.8 - local) - 0.5, 0.11)
                     * smoothstep(0.06 + local * 0.46, 0.19 + local * 0.49, opening);
        alpha = max(edge, shards * 0.76);
        ink = mix(vec3(1.0, 0.28, 0.67), vec3(0.38, 0.91, 1.0), edge);
    } else if (id == 5) { // PASTEL_POLYGONS
        vec2 grid = p * 7.0 + vec2(0.0, local * 1.7);
        vec2 cell = floor(grid);
        float seed = hashCell(cell);
        vec2 q = fract(grid) - 0.5;
        float a = atan(q.y, q.x) + seed * TAU + local;
        float shape = length(q) * cos((fract(a / TAU * 5.0) - 0.5) * TAU / 5.0);
        alpha = (1.0 - smoothstep(0.16, 0.18, shape)) * smoothstep(0.25, 0.7, seed);
        ink = mix(vec3(0.56, 0.66, 1.0), vec3(1.0, 0.53, 0.77), seed);
    } else if (id == 6) { // PERSPECTIVE_TUNNEL
        float boxRadius = max(abs(p.x) * 0.75, abs(p.y));
        float depth = log2(max(boxRadius, 0.025)) * 5.0 - local * 4.0;
        float rings = lineMask(fract(depth) - 0.5, 0.055);
        float diagonal = lineMask(abs(p.x) * 0.75 - abs(p.y), 0.0025);
        alpha = max(rings, diagonal) * smoothstep(0.02, 0.25, boxRadius);
        ink = mix(vec3(0.55, 0.28, 1.0), vec3(0.24, 0.95, 0.99), diagonal);
    } else if (id == 7) { // DIGITAL_FRAGMENT
        vec2 block = floor(uv * vec2(23.0, 14.0));
        float seed = hashCell(block);
        float offset = (seed - 0.5) * 0.18 * envelope;
        vec3 fragment = texture(sTD2DInputs[1], safeUV(uv + vec2(offset, 0.0))).rgb;
        float border = lineMask(fract(uv.y * 14.0) - 0.03, 0.018);
        alpha = step(0.66, seed) * mix(0.85, 1.0, border);
        ink = mix(fragment, vec3(0.40, 0.90, 0.86), 0.28 * border);
    } else if (id == 8) { // INK_WIPE overlay
        float stroke = valueNoise(uv * vec2(9.0, 48.0));
        float spatter = valueNoise(uv * vec2(49.0, 61.0));
        alpha = smoothstep(0.05, 0.15, 0.18 - abs(uv.x - local + 0.27 * stroke))
              * smoothstep(0.37, 0.72, 0.65 * stroke + 0.35 * spatter);
        ink = vec3(0.025, 0.037, 0.055);
    }
    return mix(rgb, ink, clamp(alpha * envelope * strength * 0.87, 0.0, 0.87));
}

void main()
{
    vec2 uv = vUV.st;
    float progress = clamp(uTransition.x, 0.0, 1.0);
    float strength = clamp(uTransition.y, 0.0, 1.0);
    float aspect = uTDOutputInfo.res.z / max(uTDOutputInfo.res.w, 1.0);
    vec2 p = (uv - uTransition.zw) * vec2(aspect, 1.0);
    vec4 current = texture(sTD2DInputs[1], uv);
    if (progress >= 1.0 && uLayers.y <= 0.0 && uLayers.zw == vec2(0.0) && uTiming.w < 0.0) {
        fragColor = TDOutputSwizzle(current);
        return;
    }

    float weight = wipeMask(int(uLayers.x), uv, p, progress, aspect);
    vec4 previous = texture(sTD2DInputs[0], uv);
    vec4 color = mix(previous, current, weight);

    float flash = clamp(uLayers.y * strength, 0.0, 0.30);
    if (flash > 0.0) {
        float light = dot(color.rgb, vec3(0.2126, 0.7152, 0.0722));
        float centerGlow = exp(-1.8 * dot(p, p));
        vec3 impact = vec3(mix(1.0 - light, light, 0.35) * 0.55 + 0.18);
        color.rgb = mix(color.rgb, impact + 0.11 * centerGlow, flash);
    }

    color.rgb = blendOverlay(color.rgb, int(uLayers.z), uTiming.x, uv, p, strength);
    color.rgb = blendOverlay(color.rgb, int(uLayers.w), uTiming.y, uv, p, strength);

#if TD_NUM_2D_INPUTS >= 3
    if (uTiming.w > 0.0 && uTiming.w < 1.0) {
        float t = uTiming.w;
        float scale = mix(0.63, 1.13, smoothstep(0.0, 0.29, t)) - 0.10 * smoothstep(0.3, 0.8, t);
        float twist = mix(-0.17, 0.08, smoothstep(0.0, 0.32, t));
        mat2 spin = mat2(cos(twist), sin(twist), -sin(twist), cos(twist));
        vec2 q = (spin * p / vec2(aspect, 1.0)) / scale + 0.5;
        if (all(greaterThan(q, vec2(0.0))) && all(lessThan(q, vec2(1.0)))) {
            vec4 type = texture(sTD2DInputs[2], q);
            float tAlpha = smoothstep(0.0, 0.10, t) * (1.0 - smoothstep(0.55, 1.0, t));
            float shadow = texture(sTD2DInputs[2], safeUV(q - vec2(0.007, -0.009))).a;
            color.rgb = mix(color.rgb, vec3(0.025, 0.04, 0.07), shadow * 0.9 * tAlpha);
            color.rgb = mix(color.rgb, vec3(0.94, 1.0, 0.66), type.a * tAlpha);
            color.a = max(color.a, type.a * tAlpha);
        }
    }
#endif

    fragColor = TDOutputSwizzle(clamp(color, 0.0, 1.0));
}
