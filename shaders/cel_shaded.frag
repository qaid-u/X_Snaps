void main() {
    vec2 uv = vUV.st;
    vec4 source = sourceAt(uv);
    vec2 gradient = luminanceGradient(uv, max(1.0, uParams.y));
    float shading = dot(gradient, normalize(vec2(-0.62, 0.78))) * uParams.z;
    float brightness = luma(source.rgb);
    float level = quantize(brightness + shading * 0.42, max(2.0, uParams.x));
    vec3 hue = mix(vec3(0.54, 0.57, 0.68), source.rgb / max(brightness, 0.08), 0.87);
    vec3 color = hue * mix(0.04, 0.92, level);
    vec3 shadowTint = vec3(0.13, 0.10, 0.30) * (1.0 - smoothstep(0.0, 0.55, level));
    float ink = smoothstep(0.10, 0.25, length(gradient)) * uParams.w;
    writeEffect(source, mix(color + shadowTint, vec3(0.025, 0.015, 0.045), ink));
}
