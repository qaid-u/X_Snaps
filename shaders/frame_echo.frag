void main() {
    vec2 uv = vUV.st;
    vec4 source = sourceAt(uv);
    vec2 offset = uParams.yz;
    vec3 ghost = sourceAt(uv + offset).rgb;
#if TD_NUM_2D_INPUTS > 1
    vec2 historyUV = clamp(uv + offset, 0.0, 1.0);
    vec4 history = texture(sTD2DInputs[1], historyUV);
    ghost = mix(ghost, history.rgb, history.a);
#endif
    vec3 ghostColor = ghost * mix(vec3(1.0), vec3(0.55, 0.94, 1.10), unit(uParams.w));
    float exposure = smoothstep(0.05, 0.43, luma(ghost)) * uParams.x;
    writeEffect(source, mix(source.rgb, max(source.rgb, ghostColor), exposure));
}
