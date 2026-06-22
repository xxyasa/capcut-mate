#include <metal_stdlib>
#include <simd/simd.h>

using namespace metal;

struct buffer_t
{
    float4x4 u_MVP;
    float4 Offset_SquareSize;
    float4x4 u_Model;
};

struct main0_out
{
    float4 chcolor [[user(chcolor)]];
    float4 dis_grad [[user(dis_grad)]];
    float4 tex_ktv [[user(tex_ktv)]];
    float2 ktv_angle [[user(ktv_angle)]];
    float smoothing_fwidth [[user(smoothing_fwidth)]];
    float4 gl_Position [[position]];
};

struct main0_in
{
    float4 position [[attribute(0)]];
    float4 charcolor [[attribute(1)]];
    float4 texcoord01 [[attribute(2)]];
    float4 texcoord23 [[attribute(3)]];
    float4 texcoord45 [[attribute(4)]];
    float4 texcoord67 [[attribute(5)]];
};

vertex main0_out main0(main0_in in [[stage_in]], constant buffer_t& buffer)
{
    main0_out out = {};
    out.gl_Position = buffer.u_MVP * float4(in.position.xy + buffer.Offset_SquareSize.xy, in.position.z, 1.0);
    out.smoothing_fwidth = (in.texcoord67.z * out.gl_Position.w) / length(buffer.u_Model[0]);
    out.chcolor = in.charcolor;
    out.dis_grad.x = in.texcoord01.x;
    out.dis_grad.y = in.texcoord01.y;
    float2 _70 = in.texcoord01.xy - in.texcoord01.zw;
    float2 _77 = _70 / (in.texcoord23.xy - in.texcoord01.zw);
    out.dis_grad.z = _77.x;
    out.dis_grad.w = _77.y;
    float2 _106 = fma(((_70 / buffer.Offset_SquareSize.zw) - float2(0.14000000059604644775390625)) * float2(1.388888835906982421875), in.texcoord45.xy, in.texcoord23.zw);
    out.tex_ktv.x = _106.x;
    out.tex_ktv.y = _106.y;
    out.tex_ktv.z = in.texcoord45.z;
    out.tex_ktv.w = in.texcoord45.w;
    out.ktv_angle = in.texcoord67.xy;
    out.gl_Position.z = (out.gl_Position.z + out.gl_Position.w) * 0.5;       // Adjust clip-space for Metal
    return out;
}

