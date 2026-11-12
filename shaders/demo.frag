float box(vec2 point, vec2 halfSize) {
    return length(max(abs(point) - halfSize, 0.0)) + min(max(abs(point.x) - halfSize.x, abs(point.y) - halfSize.y), 0.0);
}

float fillShape(float distance) {
    return 1.0 - smoothstep(-0.0015, 0.0015, distance);
}

void main() {
    vec2 uv = vUV.st;
    vec2 aspect = aspectScale();
    vec2 point = (uv - 0.5) * aspect;
    float t = uFrame.x;
    vec3 night = vec3(0.046, 0.042, 0.105);
    vec3 sea = vec3(0.05, 0.45, 0.51);
    vec3 salmon = vec3(1.0, 0.36, 0.34);
    vec3 gold = vec3(0.98, 0.77, 0.32);
    vec3 color = mix(night, sea * 0.74, smoothstep(0.05, 0.86, uv.y));
    color += vec3(0.16, 0.02, 0.10) * smoothstep(0.0, 1.0, uv.x);

    vec2 grid = point * 16.0 + vec2(t * 0.6, 0.0);
    float squares = mod(floor(grid.x) + floor(grid.y), 2.0);
    color += vec3(0.056, 0.063, 0.086) * squares * (1.0 - smoothstep(0.03, 0.22, abs(uv.x - 0.13)));

    vec2 sun = point - vec2(0.27 * aspect.x, 0.17 + 0.025 * sin(t));
    float disk = length(sun);
    float lines = smoothstep(0.10, 0.21, fract((sun.y + 0.012 * t) * 48.0));
    float sunFill = fillShape(disk - 0.158) * mix(lines, 1.0, smoothstep(-0.03, 0.09, sun.y));
    color += vec3(0.38, 0.12, 0.14) * exp(-disk * 7.0);
    color = mix(color, mix(salmon, gold, smoothstep(-0.14, 0.16, sun.y)), sunFill);
    float orbit = stroke(disk - 0.201, 0.0015);
    color = mix(color, gold, orbit * 0.52);
    vec2 orbitPoint = sun - vec2(cos(t * 0.7), sin(t * 0.7)) * 0.201;
    color = mix(color, vec3(1.0, 0.97, 0.80), fillShape(length(orbitPoint) - 0.011));

    // Moving paper-cut ridgelines and a row of silhouettes at the horizon.
    float ridge = 0.22 + 0.12 * noise2(vec2(uv.x * 7.0 + t * 0.08, 3.0))
                       + 0.08 * abs(sin(uv.x * 11.0 + t * 0.3));
    color = mix(color, vec3(0.16, 0.13, 0.31), fillShape(uv.y - ridge));
    float crest = 0.18 + 0.07 * noise2(vec2(uv.x * 12.0 - t * 0.14, 7.0));
    color = mix(color, night, fillShape(uv.y - crest));
    color = mix(color, vec3(0.36, 0.29, 0.52), stroke(uv.y - crest, 0.0018));
    vec2 city = vec2(uv.x * 41.0 + t * 0.28, uv.y);
    float height = 0.18 + hash21(vec2(floor(city.x), 18.0)) * 0.16;
    float building = fillShape(abs(fract(city.x) - 0.5) - 0.34)
        * fillShape(city.y - height) * fillShape(0.205 - city.y);
    float windows = step(0.65, fract(city.x * 3.0)) * step(0.78, fract(city.y * 125.0));
    color = mix(color, mix(night * 0.86, gold * 0.82, windows), building);

    // Motion in multiple directions exposes history, warps, and blur.
    vec2 object = point - vec2(0.25 * aspect.x * sin(t * 0.83), 0.075 + 0.08 * sin(t * 1.17));
    vec2 rotor = rotate2(t * 0.48) * object;
    float diamond = box(rotate2(0.7854) * rotor, vec2(0.099));
    float bands = 0.5 + 0.5 * sin(rotor.x * 47.0 + rotor.y * 36.0 + t * 2.0);
    vec3 objectColor = mix(vec3(0.10, 0.97, 0.81), vec3(0.07, 0.31, 0.74), bands);
    color = mix(color, objectColor, fillShape(diamond));
    color = mix(color, vec3(0.80, 1.0, 0.93), stroke(diamond, 0.0025));
    color = mix(color, salmon, fillShape(length(object) - (0.035 + 0.008 * sin(t * 3.0))));

    float star = hash21(floor(uv * vec2(100.0, 56.0)));
    float starShape = fillShape(length(fract(uv * vec2(100.0, 56.0)) - 0.5) - 0.052);
    color += vec3(0.65, 0.86, 1.0) * starShape * step(0.955, star) * step(0.56, uv.y);

    vec2 strip = (uv - vec2(0.71, 0.066)) / vec2(0.26, 0.034);
    if (all(greaterThanEqual(strip, vec2(0.0))) && all(lessThan(strip, vec2(1.0)))) {
        const vec3 swatches[7] = vec3[7](
            vec3(0.91, 0.91, 0.90), vec3(0.99, 0.80, 0.18), vec3(0.15, 0.88, 0.73),
            vec3(0.11, 0.52, 0.95), vec3(0.94, 0.30, 0.58), vec3(0.92, 0.26, 0.22),
            vec3(0.40, 0.35, 0.73));
        color = swatches[int(strip.x * 7.0)] * (0.6 + 0.4 * strip.y);
    }
    // A seven-segment graphic counter provides crisp edges on the source.
    vec2 marker = (uv - vec2(0.06, 0.066)) * vec2(50.0, 48.0);
    int second = int(mod(floor(t), 10.0));
    const int digits[10] = int[10](63, 6, 91, 79, 102, 109, 125, 7, 127, 111);
    const vec2 locations[7] = vec2[7](vec2(0.0, 0.85), vec2(0.42, 0.42), vec2(0.42, -0.42),
        vec2(0.0, -0.85), vec2(-0.42, -0.42), vec2(-0.42, 0.42), vec2(0.0, 0.0));
    for (int i = 0; i < 7; i++) {
        vec2 size = (i == 0 || i == 3 || i == 6) ? vec2(0.29, 0.07) : vec2(0.07, 0.29);
        float segment = fillShape(box(marker - locations[i], size));
        float lit = float((digits[second] >> i) & 1);
        color = mix(color, vec3(0.58, 0.98, 0.85), segment * (0.18 + 0.82 * lit));
    }
    fragColor = TDOutputSwizzle(vec4(clamp(color, 0.0, 1.0), 1.0));
}
