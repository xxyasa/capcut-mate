#include <metal_stdlib>
#include <simd/simd.h>

using namespace metal;

struct buffer_t
{
    float4x4 u_MVP;
};

struct main0_out
{
    float2 uv0 [[user(uv0)]];
    float4 gl_Position [[position]];
};

struct main0_in
{
    float4 position [[attribute(0)]];
    float2 texcoord0 [[attribute(1)]];
};

vertex main0_out main0(main0_in in [[stage_in]], constant buffer_t& buffer)
{
    main0_out out = {};
    float2 _17 = in.position.xy * 5.0;
    float4 _58 = in.position;
    _58.x = _17.x;
    float4 _60 = _58;
    _60.y = _17.y;
    out.gl_Position = buffer.u_MVP * _60;
    out.uv0 = in.texcoord0;
    out.uv0.y = 1.0 - out.uv0.y;
    out.uv0 -= float2(0.5);
    out.uv0 *= 5.0;
    out.uv0 += float2(0.5);
    out.gl_Position.z = (out.gl_Position.z + out.gl_Position.w) * 0.5;       // Adjust clip-space for Metal
    return out;
}

