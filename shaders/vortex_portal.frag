void main() {
    vec2 uv = vUV.st;
    vec4 source = sourceAt(uv);
    vec2 aspect = aspectScale();
    vec2 point = centered(uv);
    float radius = length(point);
    float portal = max(0.02, uParams.x);
    float phase = uFrame.x * 3.1;
    float rim = exp(-abs(radius - portal) * 30.0);
    float inner = 1.0 - smoothstep(portal * 0.76, portal * 1.11, radius);
    float turn = (1.0 - smoothstep(0.0, portal * 1.46, radius)) * uParams.y * (1.65 + 0.49 * sin(phase));
    float wave = sin(radius * uParams.z * SR_TAU - phase * 2.0);
    vec2 twisted = rotate2(turn) * point * (1.0 + 0.065 * wave * inner);
    vec3 scene = sourceAt(uFrame.zw + twisted / aspect).rgb;
    vec3 glow = accentColor(uOptions.z);
    vec3 graded = mix(source.rgb * vec3(0.74, 0.66, 0.90), scene * vec3(0.57, 0.88, 1.20), inner);
    float ring = smoothstep(0.65, 0.97, wave) * (inner * 0.21 + rim * 0.43);
    vec3 color = graded + glow * uParams.w * (ring + rim * 0.64);
    writeEffect(source, color);
}
