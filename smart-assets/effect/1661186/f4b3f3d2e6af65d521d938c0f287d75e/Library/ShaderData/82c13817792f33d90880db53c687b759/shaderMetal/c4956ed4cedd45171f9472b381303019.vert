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
    out.gl_Position = buffer.u_MVP * in.position;
    out.uv0 = in.texcoord0;
    out.uv0.y = 1.0 - out.uv0.y;
    out.gl_Position.z = (out.gl_Position.z + out.gl_Position.w) * 0.5;       // Adjust clip-space for Metal
    return out;
}

