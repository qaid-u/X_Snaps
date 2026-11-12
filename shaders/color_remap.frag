void main() {
    vec4 source = sourceAt(vUV.st);
    const vec3 shadows[4] = vec3[4](vec3(0.085, 0.02, 0.16), vec3(0.005, 0.13, 0.20),
        vec3(0.095, 0.025, 0.22), vec3(0.015, 0.012, 0.018));
    const vec3 middle[4] = vec3[4](vec3(0.82, 0.10, 0.73), vec3(0.02, 0.58, 0.57),
        vec3(0.50, 0.16, 0.86), vec3(0.53, 0.50, 0.54));
    const vec3 highlights[4] = vec3[4](vec3(0.97, 0.96, 0.38), vec3(1.0, 0.61, 0.25),
        vec3(0.71, 1.0, 0.24), vec3(1.0, 0.25, 0.25));
    int palette = int(mod(floor(uOptions.z), 4.0));
    float brightness = luma(source.rgb);
    float hueLean = dot(source.rgb, vec3(0.55, -0.29, -0.26));
    float value = unit((brightness - 0.5) * mix(1.0, 1.9, uParams.x) + 0.5 + hueLean * uParams.y);
    float split = mix(0.35, 0.64, unit(uParams.z));
    vec3 color = mix(shadows[palette], middle[palette], smoothstep(0.0, split, value));
    color = mix(color, highlights[palette], smoothstep(split, 1.0, value));
    writeEffect(source, color);
}
