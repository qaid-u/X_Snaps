void main() {
    vec2 uv = vUV.st;
    vec4 source = sourceAt(uv);
    int budget = uOptions.w < 0.5 ? 8 : (uOptions.w < 1.5 ? 14 : 24);
    int samples = clamp(int(uParams.y + 0.5), 4, budget);
    float pulse = 0.5 + 0.5 * sin(uOptions.x * uParams.w * SR_TAU);
    float amount = uParams.x * mix(1.0, 0.46 + 0.54 * pulse, uParams.z);
    vec2 direction = uv - uFrame.zw;
    vec3 accumulated = vec3(0.0);
    float totalWeight = 0.0;
    for (int sampleIndex = 0; sampleIndex < samples; sampleIndex++) {
        float fraction = float(sampleIndex) / float(samples - 1);
        float weight = 1.0 - 0.73 * fraction;
        accumulated += sourceAt(uv - direction * amount * fraction).rgb * weight;
        totalWeight += weight;
    }
    writeEffect(source, accumulated / totalWeight);
}
