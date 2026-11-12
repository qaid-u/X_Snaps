uniform vec4 uFrame;   // Global seconds, strength, center X, center Y
uniform vec4 uOptions; // Effect seconds, seed, palette index, quality level
uniform vec4 uParams;  // Effect-specific controls, ordered as in effects.json
layout(location = 0) out vec4 fragColor;

const float SR_PI = 3.141592653589793;
const float SR_TAU = 2.0 * SR_PI;
const vec3 SR_LUMA = vec3(0.2126, 0.7152, 0.0722);

float unit(float value) {
    return clamp(value, 0.0, 1.0);
}

float luma(vec3 color) {
    return dot(color, SR_LUMA);
}

float hash21(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

float noise2(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash21(i), hash21(i + vec2(1.0, 0.0)), f.x),
               mix(hash21(i + vec2(0.0, 1.0)), hash21(i + vec2(1.0)), f.x), f.y);
}

mat2 rotate2(float theta) {
    float c = cos(theta);
    float s = sin(theta);
    return mat2(c, s, -s, c);
}

vec2 aspectScale() {
    return vec2(uTDOutputInfo.res.z / max(1.0, uTDOutputInfo.res.w), 1.0);
}

vec2 centered(vec2 uv) {
    return (uv - uFrame.zw) * aspectScale();
}

float stroke(float distance, float width) {
    float aa = max(fwidth(distance), 0.0001);
    return 1.0 - smoothstep(width, width + aa, abs(distance));
}

float quantize(float value, float levels) {
    return floor(unit(value) * levels + 0.5) / levels;
}

vec3 quantizeColor(vec3 color, float levels) {
    return floor(clamp(color, 0.0, 1.0) * levels + 0.5) / levels;
}

float dotScreen(vec2 pixels, float period, float angle, float coverage) {
    vec2 dotUV = fract(rotate2(angle) * pixels / period) - 0.5;
    float distance = length(dotUV);
    float radius = 0.53 * sqrt(unit(coverage));
    float aa = 0.7 / period;
    return (1.0 - smoothstep(max(0.0, radius - aa), radius + aa, distance))
        * smoothstep(0.0, 0.05, coverage);
}

struct Cell {
    vec2 position;
    float nearest;
    float secondNearest;
};

Cell findCell(vec2 point, float seed) {
    vec2 base = floor(point);
    Cell cell = Cell(base, 9.0, 9.0);
    for (int y = -1; y <= 1; y++) {
        for (int x = -1; x <= 1; x++) {
            vec2 coordinate = base + vec2(x, y);
            vec2 jitter = vec2(hash21(coordinate + seed), hash21(coordinate + seed + 83.7));
            vec2 candidate = coordinate + 0.16 + 0.68 * jitter;
            vec2 delta = candidate - point;
            float distance = dot(delta, delta);
            if (distance < cell.nearest) {
                cell.secondNearest = cell.nearest;
                cell.nearest = distance;
                cell.position = candidate;
            } else {
                cell.secondNearest = min(cell.secondNearest, distance);
            }
        }
    }
    return cell;
}

vec3 accentColor(float palette) {
    const vec3 accents[4] = vec3[4](vec3(0.31, 0.98, 0.96), vec3(1.0, 0.50, 0.21),
        vec3(0.76, 1.0, 0.29), vec3(1.0, 0.20, 0.24));
    return accents[int(mod(floor(palette), 4.0))];
}

#if TD_NUM_2D_INPUTS > 0
vec4 sourceAt(vec2 uv) {
    vec2 halfTexel = uTD2DInfos[0].res.xy * 0.5;
    return texture(sTD2DInputs[0], clamp(uv, halfTexel, 1.0 - halfTexel));
}

vec2 luminanceGradient(vec2 uv, float width) {
    vec2 offset = uTD2DInfos[0].res.xy * width;
    float right = luma(sourceAt(uv + vec2(offset.x, 0.0)).rgb);
    float left = luma(sourceAt(uv - vec2(offset.x, 0.0)).rgb);
    float up = luma(sourceAt(uv + vec2(0.0, offset.y)).rgb);
    float down = luma(sourceAt(uv - vec2(0.0, offset.y)).rgb);
    return vec2(right - left, up - down);
}

void writeEffect(vec4 source, vec3 processed) {
    vec3 result = mix(source.rgb, clamp(processed, 0.0, 1.0), unit(uFrame.y));
    fragColor = TDOutputSwizzle(vec4(result, source.a));
}
#endif
