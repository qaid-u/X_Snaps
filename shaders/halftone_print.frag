void main() {
    vec2 uv = vUV.st;
    vec4 source = sourceAt(uv);
    float period = max(4.0, uParams.x);
    vec2 pixels = gl_FragCoord.xy;
    // Sample one color at each screen cell center for stable round dots.
    vec2 cellUV = (floor(pixels / period) + 0.5) * period * uTDOutputInfo.res.xy;
    vec3 cellColor = sourceAt(cellUV).rgb;
    vec3 paper = mix(vec3(0.88, 0.79, 0.63), vec3(1.0, 0.97, 0.86), unit(uParams.w));
    float black = dotScreen(pixels, period, 0.7854, (1.0 - luma(cellColor)) * uParams.y);
    vec3 mono = mix(paper, vec3(0.045, 0.050, 0.070), black * 0.97);
    vec3 cmy = 1.0 - clamp(cellColor, 0.0, 1.0);
    vec3 printColor = paper;
    printColor *= 1.0 - vec3(0.92, 0.12, 0.08) * dotScreen(pixels, period, 0.2618, cmy.x * uParams.y);
    printColor *= 1.0 - vec3(0.06, 0.88, 0.16) * dotScreen(pixels, period, 1.3090, cmy.y * uParams.y);
    printColor *= 1.0 - vec3(0.08, 0.10, 0.92) * dotScreen(pixels, period, 0.0, cmy.z * uParams.y);
    writeEffect(source, mix(mono, printColor, unit(uParams.z)));
}
