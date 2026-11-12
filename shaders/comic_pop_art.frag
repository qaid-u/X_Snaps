void main() {
    vec2 uv = vUV.st;
    vec4 source = sourceAt(uv);
    float brightness = luma(source.rgb);
    float threshold = mix(0.26, 0.58, unit(uParams.w));
    float light = smoothstep(threshold + 0.18, threshold + 0.20, brightness);
    float mid = smoothstep(threshold - 0.02, threshold + 0.02, brightness);
    vec3 saturation = mix(vec3(brightness), source.rgb, 1.72);
    vec3 ink = vec3(0.055, 0.030, 0.100);
    vec3 shadow = mix(ink, vec3(0.30, 0.07, 0.40), 0.62 + saturation.r * 0.32);
    vec3 midtone = clamp(saturation * 1.1 + vec3(0.22, 0.08, 0.09), 0.0, 1.0);
    vec3 paper = mix(vec3(1.0, 0.91, 0.70), midtone, 0.36);
    vec3 color = mix(mix(shadow, midtone, mid), paper, light);
    float dots = dotScreen(gl_FragCoord.xy, max(4.0, uParams.y), 0.51, 0.7 * (1.0 - brightness));
    color = mix(color, ink, dots * (0.32 + 0.31 * mid) * (1.0 - light));
    float edge = smoothstep(0.055, 0.24, length(luminanceGradient(uv, max(1.0, uParams.x))));
    vec2 margin = min(uv, 1.0 - uv) * uTDOutputInfo.res.zw;
    float panel = min(margin.x, margin.y);
    float border = 1.0 - smoothstep(uParams.z - 1.0, uParams.z + 1.0, panel);
    color = mix(color, ink, max(edge, border * 0.95));
    writeEffect(source, color);
}
