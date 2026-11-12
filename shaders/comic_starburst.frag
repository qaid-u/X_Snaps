void main() {
    vec2 uv = vUV.st;
    vec4 source = sourceAt(uv);
    vec2 point = centered(uv);
    float angle = atan(point.y, point.x + 0.000001) / SR_TAU + 0.5;
    float radius = length(point);
    float time = uOptions.x * uParams.w;
    float count = max(5.0, round(uParams.x));
    float zigzag = abs(fract(angle * count + time * 0.11) - 0.5) * 2.0;
    float size = uParams.y * (0.87 + 0.13 * sin(time));
    float distance = radius - size * mix(0.63, 1.24, zigzag);
    float burst = 1.0 - smoothstep(-0.003, 0.003, distance);
    float outline = stroke(distance, 0.007);
    float rayUV = angle * (count * 3.0) + time * 0.12;
    float ray = 1.0 - smoothstep(0.05, 0.18, abs(fract(rayUV) - 0.5));
    ray *= smoothstep(size * 0.85, size * 1.57, radius);
    vec3 paper = accentColor(uOptions.z + 1.0);
    float brightness = luma(source.rgb);
    vec3 pop = mix(source.rgb * vec3(0.82, 0.72, 1.11),
        paper * (0.42 + 0.58 * quantize(brightness, 4.0)), burst * uParams.z);
    float dot = dotScreen(gl_FragCoord.xy, 9.5, 0.78, 0.83 * (1.0 - brightness));
    vec3 ink = vec3(0.056, 0.027, 0.10);
    writeEffect(source, mix(pop, ink, clamp(outline * 0.85 + ray * 0.29 + dot * burst * 0.37, 0.0, 1.0)));
}
