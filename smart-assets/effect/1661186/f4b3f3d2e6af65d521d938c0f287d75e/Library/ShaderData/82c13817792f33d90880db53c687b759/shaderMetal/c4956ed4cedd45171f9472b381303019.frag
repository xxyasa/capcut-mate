#include <metal_stdlib>
#include <simd/simd.h>

using namespace metal;

struct buffer_t
{
    float2 blur_val;
    float fade_val;
};

struct main0_out
{
    float4 gl_FragColor [[color(0)]];
};

struct main0_in
{
    float2 uv0 [[user(uv0)]];
};

fragment main0_out main0(main0_in in [[stage_in]], constant buffer_t& buffer, texture2d<float> _MainTex [[texture(0)]], sampler _MainTexSmplr [[sampler(0)]])
{
    main0_out out = {};
    out.gl_FragColor = _MainTex.sample(_MainTexSmplr, in.uv0);
    out.gl_FragColor *= smoothstep(buffer.blur_val.x, buffer.blur_val.x + buffer.blur_val.y, in.uv0.x);
    out.gl_FragColor *= buffer.fade_val;
    return out;
}

