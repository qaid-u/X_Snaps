void main() {
    vec2 uv = vUV.st;
    vec4 source = sourceAt(uv);
    vec2 aspect = aspectScale();
    float density = max(2.0, uParams.x);
    vec2 point = centered(uv) * density;
    Cell cell = findCell(point, uOptions.y + 79.0);
    float random = hash21(cell.position * 1.73);
    float motion = (0.5 + 0.5 * sin(uOptions.x * 1.37 + random * 3.0)) * 0.52 + 0.48;
    float shift = uParams.y * motion;
    vec2 facet = rotate2((random - 0.5) * 2.7 * uParams.w * motion) * (point - cell.position);
    vec2 outwards = normalize(cell.position + vec2(0.00001));
    vec2 mapped = uFrame.zw + (cell.position + facet - outwards * shift) / (density * aspect);
    vec3 shard = sourceAt(mapped).rgb * (0.66 + random * 0.50);
    float distance = cell.secondNearest - cell.nearest;
    float gap = smoothstep(uParams.z * shift, uParams.z * shift + 0.026, distance);
    float rim = stroke(distance - uParams.z * shift - 0.025, 0.012) * shift;
    vec3 crack = mix(vec3(0.036, 0.039, 0.069), source.rgb * 0.29, 0.42);
    vec3 color = mix(crack, shard, gap) + rim * vec3(0.34, 0.56, 0.66);
    writeEffect(source, color);
}
