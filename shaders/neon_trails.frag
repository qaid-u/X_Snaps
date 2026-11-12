void main() {
    vec2 uv = vUV.st;
    vec4 source = sourceAt(uv);
    vec2 direction = vec2(1.0, 0.28 + 0.14 * sin(uFrame.x));
    vec2 texel = uTD2DInfos[0].res.xy;
    float threshold = 0.46;
    float bright = smoothstep(threshold, 0.89, luma(source.rgb));
    float halo = 0.0;
    int budget = uOptions.w < 0.5 ? 3 : (uOptions.w < 1.5 ? 5 : 8);
    for (int i = 1; i <= budget; i++) {
        vec2 offset = direction * texel * uParams.z * float(i);
        halo += max(0.0, luma(sourceAt(uv + offset).rgb) - threshold)
            + max(0.0, luma(sourceAt(uv - offset).rgb) - threshold);
    }
    halo /= float(budget);
    vec3 light = accentColor(uOptions.z);
    vec3 color = source.rgb * vec3(0.44, 0.46, 0.62) + (bright * 0.69 + halo) * light * uParams.w;
#if TD_NUM_2D_INPUTS > 1
    vec2 offset = direction * uParams.y;
    vec4 trace = texture(sTD2DInputs[1], clamp(uv + offset, 0.0, 1.0));
    float emission = smoothstep(0.19, 0.70, luma(trace.rgb)) * trace.a;
    color = max(color, trace.rgb * emission * uParams.x * light);
#else
    float tail = smoothstep(threshold, 0.90, luma(sourceAt(uv + direction * uParams.y).rgb));
    color += tail * light * uParams.x * 0.35;
#endif
    writeEffect(source, color);
}
