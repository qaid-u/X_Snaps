void main() {
    vec2 uv = vUV.st;
    vec4 source = sourceAt(uv);
    float horizon = clamp(uParams.x, 0.04, 0.96);
    float distance = horizon - uv.y;
    float depth = 1.0 / max(0.016, distance);
    float density = max(5.0, uParams.y);
    vec2 gridUV = vec2(centered(uv).x * depth * density * 0.18,
        depth * density * 0.08 + uFrame.x * 2.1);
    vec2 grid = abs(fract(gridUV) - 0.5);
    vec2 aa = clamp(fwidth(gridUV), vec2(0.02), vec2(0.30));
    vec2 wire = 1.0 - smoothstep(vec2(0.01), 0.01 + aa, grid);
    float floorMask = smoothstep(0.014, 0.10, distance);
    float glow = exp(-abs(distance) * 34.0);
    vec3 pink = mix(vec3(0.98, 0.18, 0.76), accentColor(uOptions.z), 0.45);
    vec3 cyan = vec3(0.12, 0.86, 1.0);
    vec3 graded = mix(source.rgb * vec3(0.72, 0.61, 0.91), source.rgb, 0.50);
    vec3 line = mix(pink, cyan, smoothstep(0.04, 0.42, distance));
    vec2 starCell = uv * vec2(114.0, 68.0);
    float random = hash21(floor(starCell) + uOptions.y);
    float star = (1.0 - smoothstep(0.02, 0.14, length(fract(starCell) - 0.5)))
        * step(1.0 - uParams.w * 0.13, random) * smoothstep(horizon, horizon + 0.27, uv.y);
    vec3 color = graded + line * floorMask * max(wire.x, wire.y) * uParams.z
        + pink * glow * 0.31 + cyan * star * (0.65 + 0.35 * sin(uFrame.x * 4.0 + random * 49.0));
    writeEffect(source, color);
}
