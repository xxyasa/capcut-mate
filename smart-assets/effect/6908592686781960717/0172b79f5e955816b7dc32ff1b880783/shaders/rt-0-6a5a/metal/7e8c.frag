#include <metal_stdlib>
#include <simd/simd.h>

using namespace metal;

struct main0_out
{
    float4 gl_FragColor [[color(0)]];
};

struct main0_in
{
    float2 uv0 [[user(uv0)]];
};

fragment main0_out main0(main0_in in [[stage_in]], texture2d<float> _MainTex [[texture(0)]], sampler _MainTexSmplr [[sampler(0)]])
{
    main0_out out = {};
    float4 color = float4(0.0);
    float2 uv = in.uv0;
    color = _MainTex.sample(_MainTexSmplr, uv);
    out.gl_FragColor = color;
    return out;
}

