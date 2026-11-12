void main() {
    vec2 uv = vUV.st;
    vec4 source = sourceAt(uv);
    float brightness = luma(source.rgb);
    float threshold = 0.42 + 0.065 * sin(uOptions.x * 0.55);
    float contrast = mix(0.20, 0.047, unit(uParams.x));
    float white = smoothstep(threshold - contrast, threshold + contrast, brightness);
    vec2 pixel = gl_FragCoord.xy;
    float hatch = (pixel.x + pixel.y * 0.86) * uParams.z * 0.138;
    float line = 1.0 - smoothstep(0.10, 0.24, abs(fract(hatch) - 0.5));
    float tintMask = smoothstep(0.17, 0.39, brightness) * (1.0 - smoothstep(0.56, 0.77, brightness));
    white *= 1.0 - 0.79 * tintMask * line;
    float swipe = (uv.x * 0.63 + uv.y * 0.37) - uParams.w - sin(uOptions.x * 0.66) * 0.055;
    float slash = 1.0 - smoothstep(0.004, 0.008, abs(swipe));
    vec3 ink = vec3(0.035, 0.032, 0.048);
    vec3 paper = vec3(0.93, 0.94, 0.90);
    vec3 color = mix(ink, paper, white);
    float saturation = max(max(source.r, source.g), source.b) - min(min(source.r, source.g), source.b);
    float colorMask = smoothstep(0.20, 0.54, saturation) * smoothstep(-0.12, 0.04, swipe);
    vec3 accent = accentColor(uOptions.z + 3.0);
    color = mix(color, accent * (0.35 + 0.65 * white), max(colorMask, slash) * uParams.y);
    writeEffect(source, mix(color, ink, slash * (1.0 - uParams.y) * 0.8));
}
