void main() {
    vec2 uv = vUV.st;
    vec4 source = sourceAt(uv);
    vec2 p = gl_FragCoord.xy;
    vec2 texel = uTD2DInfos[0].res.xy;
    vec2 wobble = vec2(noise2(p * 0.18), noise2(p * 0.15 + 23.0)) - 0.5;
    vec2 inkUV = uv + wobble * texel * 1.75;
    float edge = length(luminanceGradient(inkUV, max(1.0, uParams.x)));
    vec3 paint = quantizeColor(sourceAt(inkUV).rgb, max(2.0, floor(uParams.y + 0.5)));
    vec3 paper = mix(vec3(0.87, 0.94, 0.98), vec3(1.0, 0.89, 0.73), unit(uParams.w));
    float fiber = (noise2(p * vec2(0.24, 0.7)) * 0.65 + hash21(p) * 0.35) - 0.5;
    paint = mix(paint * 0.79 + 0.10, paper, 0.17) * (1.0 + fiber * uParams.z * 0.35);
    vec3 ink = vec3(0.08, 0.10, 0.16);
    vec3 color = mix(paint, ink, smoothstep(0.04, 0.23, edge) * 0.92);
    writeEffect(source, color);
}
