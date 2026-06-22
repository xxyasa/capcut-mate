#include <metal_stdlib>
#include <simd/simd.h>

using namespace metal;

struct main0_out
{
    float4 FragColor [[color(0)]];
    float gl_FragDepth [[depth(any)]];
};

fragment main0_out main0()
{
    main0_out out = {};
    out.FragColor = float4(0.0);
    out.gl_FragDepth = 1.0;
    return out;
}

