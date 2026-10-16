#version 460 core
uniform vec4 primitiveColor;
uniform vec2 gradientBounds;
uniform int gradientKind;
in float ndcY;
layout(location = 0) out vec4 color;
void main() {
    color = primitiveColor;
    if (gradientBounds.y > gradientBounds.x) {
        // Exact CST measured-response gradient stops, from top to bottom.
        float t = clamp((gradientBounds.y - ndcY) / (gradientBounds.y - gradientBounds.x), 0.0, 1.0);
        if (gradientKind == 5) {
            color = vec4(mix(vec3(17,18,21),vec3(10,11,13),t)/255.0,1);
            return;
        }
        if (gradientKind == 6) {
            color.a *= mix(4.0,32.0,t)/255.0;
            return;
        }
        if (gradientKind == 3) {
            float a = t < .45 ? mix(70.0,28.0,t/.45) : mix(28.0,0.0,(t-.45)/.55);
            color.a *= a / 255.0;
            return;
        }
        if (gradientKind == 4) {
            color.a *= mix(240.0,120.0,t)/255.0;
            return;
        }
        if (gradientKind == 2) {
            // CST transport shadow: alpha 110,66,19.8,0 at 0,.35,.75,1.
            float a = t < .35 ? mix(110.0,66.0,t/.35)
                : t < .75 ? mix(66.0,20.0,(t-.35)/.40)
                : mix(20.0,0.0,(t-.75)/.25);
            color.a *= a / 255.0;
            return;
        }
        if (gradientKind == 1) {
            // CST controller_theme.TrendPlot uses a different RGB/alpha fill.
            vec4 a = vec4(255,178,72,150) / 255.0;
            vec4 b = vec4(244,120,24,115) / 255.0;
            vec4 c = vec4(190,62,10,55) / 255.0;
            vec4 d = vec4(45,10,0,8) / 255.0;
            color = t < 0.38 ? mix(a,b,t/0.38) : t < 0.72 ? mix(b,c,(t-0.38)/0.34) : mix(c,d,(t-0.72)/0.28);
            color.a *= primitiveColor.a;
            return;
        }
        float a = t < 0.42 ? mix(145.0, 90.0, t / 0.42)
            : t < 0.78 ? mix(90.0, 35.0, (t - 0.42) / 0.36)
            : mix(35.0, 5.0, (t - 0.78) / 0.22);
        color.a *= a / 255.0;
    }
}
