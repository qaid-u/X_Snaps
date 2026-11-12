void main() {
    vec2 uv = vUV.st;
    vec4 source = sourceAt(uv);
    vec2 texel = uTD2DInfos[0].res.xy;
    vec3 nearby = (sourceAt(uv + vec2(3.0, 1.0) * texel).rgb
        + sourceAt(uv - vec2(3.0, 1.0) * texel).rgb
        + sourceAt(uv + vec2(-1.0, 3.0) * texel).rgb
        + sourceAt(uv - vec2(-1.0, 3.0) * texel).rgb) * 0.25;
    vec3 detail = max(source.rgb + (source.rgb - nearby) * uParams.x * 0.9, 0.0);
    vec3 bloom = (sourceAt(uv + vec2(11.0, 0.0) * texel).rgb
        + sourceAt(uv - vec2(11.0, 0.0) * texel).rgb
        + sourceAt(uv + vec2(0.0, 11.0) * texel).rgb
        + sourceAt(uv - vec2(0.0, 11.0) * texel).rgb) * 0.25;
    float depth = smoothstep(0.07, 0.78, luma(nearby));
    vec3 grade = mix(vec3(0.74, 0.94, 1.17), vec3(1.16, 1.01, 0.86), depth);
    vec3 curve = smoothstep(vec3(0.03), vec3(0.93), detail * grade);
    vec2 point = (uv - vec2(0.49, 0.57)) * aspectScale();
    float vignette = 1.0 - smoothstep(0.13, 1.0, length(point)) * uParams.z;
    float grain = hash21(floor(gl_FragCoord.xy) + floor(uFrame.x * 24.0) + uOptions.y) - 0.5;
    vec3 color = curve * vignette + bloom * smoothstep(0.42, 0.9, luma(bloom)) * uParams.y * 0.55;
    writeEffect(source, color + grain * uParams.w * 0.105);
}
