#include <metal_stdlib>
#include <simd/simd.h>

using namespace metal;

struct buffer_t
{
    float4 _Scale2_Smoothing_AnimAlpha;
    float4 _Color1;
};

struct main0_out
{
    float4 gl_FragColor [[color(0)]];
};

struct main0_in
{
    float4 chcolor [[user(chcolor)]];
    float4 dis_grad [[user(dis_grad)]];
    float4 tex_ktv [[user(tex_ktv)]];
    float2 ktv_angle [[user(ktv_angle)]];
    float smoothing_fwidth [[user(smoothing_fwidth)]];
};

fragment main0_out main0(main0_in in [[stage_in]], constant buffer_t& buffer, texture2d<float> _MainTex [[texture(0)]], sampler _MainTexSmplr [[sampler(0)]])
{
    main0_out out = {};
    float _60 = buffer._Scale2_Smoothing_AnimAlpha.z + in.smoothing_fwidth;
    float4 _76 = _MainTex.sample(_MainTexSmplr, in.dis_grad.xy);
    float _91 = smoothstep(0.0, 0.100000001490116119384765625, buffer._Scale2_Smoothing_AnimAlpha.z);
    float _100 = fma(dot(_76.xy, float2(0.00390625, 1.0)), 1.0 - _91, dot(_76.zw, float2(0.00390625, 1.0)) * _91);
    float _104 = 1.0 - buffer._Scale2_Smoothing_AnimAlpha.x;
    float _107 = fast::clamp(_104 - _60, 0.0, 1.0);
    float _122 = 1.0 - buffer._Scale2_Smoothing_AnimAlpha.y;
    float _125 = fast::clamp(_122 - _60, 0.0, 1.0);
    float4 _141 = buffer._Color1 * in.chcolor;
    float _161 = step(in.tex_ktv.w, 0.0);
    float _169 = step(fma(in.dis_grad.z, in.ktv_angle.x, in.dis_grad.w * in.ktv_angle.y), in.tex_ktv.z);
    float _181 = ((1.0 - fast::clamp((_100 - _107) / ((_104 + _60) - _107), 0.0, 1.0)) * fast::clamp((_100 - _125) / ((_122 + _60) - _125), 0.0, 1.0)) * fma(1.0 - _169, _161, _169 * (1.0 - _161));
    float _190 = _141.w;
    float3 _191 = (_141.xyz * _181) * _190;
    out.gl_FragColor = float4(_191, _190 * _181);
    return out;
}

