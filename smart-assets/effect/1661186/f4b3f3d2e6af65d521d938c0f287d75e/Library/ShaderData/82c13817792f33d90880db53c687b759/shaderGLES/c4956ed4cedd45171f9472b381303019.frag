#define AE_AreaLightNum 0
#define AE_DirLightNum 0
#define AE_PointLightNum 0
#define AE_SpotLightNum 0
precision highp float;

uniform sampler2D _MainTex;
varying vec2 uv0;

uniform float fade_val;
uniform vec2 blur_val;

void main()
{
    vec4 color = texture2D(_MainTex, uv0);
    // color.rgb *= 
    // color.a = fade_val;
    gl_FragColor = color;
    gl_FragColor *= smoothstep(blur_val.x, blur_val.x + blur_val.y, uv0.x);
    gl_FragColor.rgba *= fade_val;
    // gl_FragColor = vec4(1,0, 0, 1);
}
