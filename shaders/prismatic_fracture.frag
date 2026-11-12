void main() {
    vec2 uv = vUV.st;
    vec4 source = sourceAt(uv);
    vec2 aspect = aspectScale();
    float density = max(2.0, uParams.x);
    vec2 point = centered(uv) * density;
    Cell cell = findCell(point, uOptions.y + 3.0);
    vec2 facet = point - cell.position;
    float random = hash21(cell.position + uOptions.y);
    float angle = mix(-1.6, 1.6, random) * uParams.y + 0.17 * sin(uFrame.x + random * 27.0);
    vec2 shifted = rotate2(angle) * facet + cell.position;
    shifted += vec2(cos(random * 45.0), sin(random * 45.0)) * uParams.y * 0.65;
    vec2 mapped = uFrame.zw + shifted / (density * aspect);
    vec2 spread = vec2(cos(angle), sin(angle)) * uParams.z / aspect;
    vec3 crystal = vec3(sourceAt(mapped + spread).r, sourceAt(mapped).g, sourceAt(mapped - spread).b);
    vec3 rainbow = 0.77 + 0.32 * cos(SR_TAU * (random + vec3(0.0, 0.33, 0.67)));
    float seam = 1.0 - smoothstep(0.01, 0.075, cell.secondNearest - cell.nearest);
    vec3 rim = mix(vec3(0.35, 0.82, 1.0), vec3(1.0, 0.40, 0.80), random);
    writeEffect(source, mix(crystal * rainbow + rainbow * 0.1, rim, seam * uParams.w));
}
