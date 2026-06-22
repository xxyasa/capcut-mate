precision lowp float;
varying vec4 chcolor;
varying vec4 dis_grad;
varying vec4 tex_ktv;
varying vec2 ktv_angle;
varying float smoothing_fwidth;

uniform highp sampler2D _MainTex;
#ifdef _TEXTURE
uniform sampler2D _Diffuse;
#endif

uniform vec4 _Color1;
uniform vec4 _Color1_2;
uniform vec4 _Color2;
uniform vec4 _Color2_3;
uniform vec4 _Color3;
uniform vec4 _ControlPercent;
uniform vec4 _ColorPercent;
uniform vec4 _AngleVec;
uniform vec4 _Scale2_Smoothing_AnimAlpha;
uniform vec2 _ShadowScale;
uniform float _ExtraSmoothing;

const highp float oneConst = 1.0;
const highp float halfConst = 0.5;
const highp float zeroConst = 0.0;
const highp vec2 bitSh16 = vec2(256., 1.);
const highp vec2 bitMsk16 = vec2(0., 1. / 256.);
const highp vec2 bitShifts16 = vec2(1.) / bitSh16;
highp float unpack16(highp vec2 color) { return dot(color, bitShifts16); }

float linearstep(float edge0, float edge1, float x) {
  float t = (x - edge0) / (edge1 - edge0);
  return clamp(t, 0.0, 1.0);
}

void main()
{
    //float extraSmoothing = 0.005;
    float scale2_Smoothing_AnimAlpha_x = _Scale2_Smoothing_AnimAlpha.x;
    float scale2_Smoothing_AnimAlpha_y = _Scale2_Smoothing_AnimAlpha.y;
    // gradient color
    float smoothing = _Scale2_Smoothing_AnimAlpha.z + smoothing_fwidth;
    vec4 cc = _Color1;
    float x = zeroConst;
#ifdef _COLOR2
    float gradDist = ((dis_grad.z - halfConst) * _AngleVec.r + (dis_grad.w - halfConst) * _AngleVec.g)/_AngleVec.b + halfConst;
#ifdef _LINEAR
    x = clamp(gradDist, _ColorPercent.x, _ControlPercent.x);
    x = (x - _ColorPercent.x)/(_ControlPercent.x - _ColorPercent.x);
    cc = mix(cc, _Color1_2, x);

    x = clamp(gradDist, _ControlPercent.x, _ColorPercent.y);
    x = (x - _ControlPercent.x)/(_ColorPercent.y - _ControlPercent.x);
    cc = mix(cc, _Color2, x);
#else
    x = linearstep(_ControlPercent.x - halfConst * smoothing, _ControlPercent.x + halfConst * smoothing, gradDist);
    cc = mix(cc, _Color2, x);
#endif

#ifdef _COLOR3
#ifdef _LINEAR
    x = clamp(gradDist, _ColorPercent.y, _ControlPercent.y);
    x = (x - _ColorPercent.y) / (_ControlPercent.y - _ColorPercent.y);
    cc = mix(cc, _Color2_3, x);

    x = clamp(gradDist, _ControlPercent.y, _ColorPercent.z);
    x = (x - _ControlPercent.y) / (_ColorPercent.z - _ControlPercent.y);
    cc = mix(cc, _Color3, x);
#else
    x = linearstep(_ControlPercent.y - 0.4 * smoothing, _ControlPercent.y + 0.4 * smoothing, gradDist);
    cc = mix(cc, _Color3, x);
#endif
#endif
#endif

#ifdef _TEXTURE
    vec4 diff = texture2D(_Diffuse, vec2(tex_ktv.x, oneConst - tex_ktv.y)) * _Scale2_Smoothing_AnimAlpha.w;
    cc = cc * (1.0 - diff.a) + diff;
#endif
    
    highp vec4 dis_tex = texture2D(_MainTex, dis_grad.xy);
    highp float distance_smooth = unpack16(dis_tex.ba);
    highp float distance_clear = unpack16(dis_tex.rg);
    highp float ratio = smoothstep(zeroConst, 0.1, _Scale2_Smoothing_AnimAlpha.z);
    highp float distance = distance_clear*(oneConst-ratio) + distance_smooth*ratio;
    float alpha = oneConst;
    float l = clamp(oneConst - scale2_Smoothing_AnimAlpha_x - smoothing, zeroConst, oneConst);
    alpha *= oneConst - linearstep(l, oneConst - scale2_Smoothing_AnimAlpha_x + smoothing, distance);
    l = clamp(oneConst - scale2_Smoothing_AnimAlpha_y - smoothing, zeroConst, oneConst);
    alpha *= linearstep(l, oneConst - scale2_Smoothing_AnimAlpha_y + smoothing, distance);
    cc *= chcolor;
#ifdef _INNER_SHADOW
    float inner_dis = unpack16(texture2D(_MainTex, dis_grad.xy + _ShadowScale).rg);
    float inner_alpha = linearstep(halfConst - smoothing, halfConst + smoothing, inner_dis);
    alpha *= inner_alpha;
#endif

#ifndef KTV_DISABLE
    float ktvDist = dis_grad.z * ktv_angle.x + dis_grad.w * ktv_angle.y;
    float alpha_less = step(tex_ktv.w, zeroConst);
    float alpha_greater = oneConst - alpha_less;
    float ktv_right = step(ktvDist, tex_ktv.z);
    float ktv_alpha = (oneConst - ktv_right) * alpha_less + ktv_right * alpha_greater;
    alpha *= ktv_alpha;
#endif
    gl_FragColor = vec4(cc.rgb * alpha * cc.a, cc.a * alpha);
}
