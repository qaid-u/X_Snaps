void main() {
    vec2 uv = vUV.st;
    vec4 source = sourceAt(uv);
    float t = uFrame.x * max(0.1, uParams.w);
    float tick = floor(t * 12.0);
    vec2 block = floor(uv * vec2(8.0, 19.0));
    float displacement = hash21(block + vec2(tick, uOptions.y));
    float strip = hash21(vec2(floor(uv.y * 43.0), tick + uOptions.y));
    float pulse = smoothstep(0.65, 1.0, hash21(vec2(floor(t * 2.0), uOptions.y)));
    float slip = (displacement - 0.5) * step(0.8, displacement) * uParams.y;
    slip += (strip - 0.5) * step(0.89, strip) * uParams.y * pulse;
    float spread = uParams.x * (1.0 + pulse * 1.8);
    vec2 shifted = uv + vec2(slip + 0.002 * sin(uv.y * 103.0 + t * 31.0), 0.0);
    vec3 color = vec3(sourceAt(shifted + vec2(spread, 0.0)).r,
                      sourceAt(shifted).g,
                      sourceAt(shifted - vec2(spread, 0.0)).b);
    float scan = 0.5 + 0.5 * cos(gl_FragCoord.y * 1.57 + t * 9.0);
    color *= 1.0 - scan * unit(uParams.z) * (0.55 + pulse * 0.45);
    writeEffect(source, color);
}
