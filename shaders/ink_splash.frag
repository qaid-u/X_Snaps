void main() {
    vec2 uv = vUV.st;
    vec4 source = sourceAt(uv);
    vec2 point = centered(uv);
    float time = uFrame.x * uParams.w;
    vec2 seed = vec2(uOptions.y, uOptions.y * 0.37);
    vec2 brush = rotate2(-0.41) * point;
    float scale = max(2.0, uParams.y);
    float mottles = noise2((brush + vec2(0.04 * time, 0.0)) * scale + seed) * 0.68
        + noise2(brush * scale * 4.3 + seed * 2.0) * 0.32;
    float fibers = noise2(brush * vec2(7.0, 130.0) + seed);
    float contour = mottles - 0.24 * length(point) + uParams.z * (fibers - 0.5) * 0.23;
    float boundary = mix(0.73, 0.34, unit(uParams.x)) + 0.06 * sin(time);
    float ink = smoothstep(boundary - 0.035, boundary + 0.035, contour);
    float surface = 0.90 + 0.20 * fibers;
    vec3 paper = mix(vec3(luma(source.rgb)), source.rgb, 0.68) * surface;
    vec3 blot = vec3(0.037, 0.025, 0.10) + source.rgb * 0.22;
    writeEffect(source, mix(paper, blot, ink * 0.86));
}
