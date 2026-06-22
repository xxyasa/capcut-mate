#include <metal_stdlib>
#include <simd/simd.h>

using namespace metal;

struct buffer_t
{
    float u_angle;
    float u_uvOffset;
    float u_blackRange;
    float u_blackSmoothRange;
    float u_minAlpha;
};

struct main0_out
{
    float4 gl_FragColor [[color(0)]];
};

struct main0_in
{
    float2 fTexCoord [[user(fTexCoord)]];
};

fragment main0_out main0(main0_in in [[stage_in]], constant buffer_t& buffer, texture2d<float> _MainTex [[texture(0)]], sampler _MainTexSmplr [[sampler(0)]])
{
    main0_out out = {};
    float2 _22 = float2(in.fTexCoord.x, 1.0 - in.fTexCoord.y);
    float4 _32 = _MainTex.sample(_MainTexSmplr, _22);
    float _111 = -buffer.u_uvOffset;
    float _122 = fma(buffer.u_angle, 0.01745329238474369049072265625, 0.78539812564849853515625);
    float _123 = tan(_122);
    float2 _147 = float3(_123, -1.0, 0.0).xy;
    float _160 = abs(dot(_147, _22) + fma(_111, sign(cos(_122)), fma(fma(_111, sign(sin(_122)), -0.5), _123, 0.5))) / sqrt(dot(_147, _147));
    float _191 = _32.w;
    float4 _201 = mix(_32, (float4(1.0, 1.0, 0.89803922176361083984375, 1.0) * fma(1.0 - smoothstep(buffer.u_blackRange, buffer.u_blackRange + 0.89999997615814208984375, _160), 0.4000000059604644775390625, 1.0)) * _191, float4(fma(1.0 - smoothstep(buffer.u_blackRange - buffer.u_blackSmoothRange, buffer.u_blackRange, _160), 1.0 - buffer.u_minAlpha, buffer.u_minAlpha)));
    out.gl_FragColor.x = _201.x;
    out.gl_FragColor.y = _201.y;
    out.gl_FragColor.z = _201.z;
    out.gl_FragColor.w = _191;
    return out;
}

