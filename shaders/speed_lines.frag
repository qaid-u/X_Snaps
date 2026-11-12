void main() {
    vec2 uv = vUV.st;
    vec4 source = sourceAt(uv);
    vec2 point = centered(uv);
    float radius = length(point);
    float angle = atan(point.y, point.x + 0.000001) / SR_TAU;
    float density = max(1.0, round(uParams.x));
    float radial = (angle + 0.5) * density;
    float linear = point.y * density + point.x * 2.2;
    float streak = mix(linear, radial, unit(uParams.w));
    float stripe = abs(fract(streak) - 0.5);
    float sector = floor(streak);
    float seed = hash21(vec2(sector, uOptions.y));
    float start = uParams.z + 0.35 * seed + 0.08 * sin(seed * 97.0 + uFrame.x * 4.8);
    float edge = min(fwidth(streak), 0.45);
    float ray = 1.0 - smoothstep(0.035 + 0.14 * seed, 0.045 + 0.14 * seed + edge, stripe);
    ray *= smoothstep(start, start + 0.18, radius) * uParams.y;
    vec3 rayColor = mix(vec3(0.57, 0.97, 1.0), vec3(1.0, 0.93, 0.58), mod(floor(uOptions.z), 2.0));
    vec3 color = mix(source.rgb, source.rgb * 0.66, smoothstep(0.3, 0.9, radius) * 0.57);
    writeEffect(source, mix(color, rayColor, ray * (0.45 + seed * 0.55)));
}
