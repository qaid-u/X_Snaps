void main() {
    vec4 source = sourceAt(vUV.st);
    float levels = max(2.0, floor(uParams.x + 0.5));
    vec2 pixel = floor(gl_FragCoord.xy);
    float dither = (hash21(pixel + uOptions.y) - 0.5) * uParams.y / levels;
    float blend = unit(uParams.z);
    vec3 vivid = mix(vec3(luma(source.rgb)), source.rgb, 1.25);
    vec3 rgb = quantizeColor(vivid + dither, levels);
    vec3 perceptual = pow(quantizeColor(sqrt(max(vivid, 0.0)) + dither, levels), vec3(2.0));
    writeEffect(source, mix(rgb, perceptual, blend));
}
