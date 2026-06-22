#include <metal_stdlib>
#include <simd/simd.h>

using namespace metal;

struct buffer_t
{
    float4x4 u_MVP;
};

struct main0_out
{
    float2 fTexCoord [[user(fTexCoord)]];
    float4 gl_Position [[position]];
};

struct main0_in
{
    float2 position [[attribute(0)]];
    float2 texcoord0 [[attribute(1)]];
};

vertex main0_out main0(main0_in in [[stage_in]], constant buffer_t& buffer)
{
    main0_out out = {};
    out.fTexCoord.x = in.texcoord0.x;
    out.fTexCoord.y = in.texcoord0.y;
    out.gl_Position = buffer.u_MVP * float4(in.position, 0.0, 1.0);
    out.gl_Position.z = (out.gl_Position.z + out.gl_Position.w) * 0.5;       // Adjust clip-space for Metal
    return out;
}

