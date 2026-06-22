#include <metal_stdlib>
#include <simd/simd.h>

using namespace metal;

struct buffer_t
{
    float s1;
    float4 textSize;
    float b1;
    float s2;
    float b2;
    float a2;
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
    float2 _115 = in.uv0 - float2(0.5);
    float2 _121 = _115 / float2(buffer.s1);
    float2 _204 = float2(1.0, buffer.textSize.x / buffer.textSize.y);
    float2 _206 = _121 / _204;
    float4 _333;
    _333 = _MainTex.sample(_MainTexSmplr, (_121 + float2(0.5)));
    for (int _332 = 1; _332 <= 30; )
    {
        float _217 = (float(_332) * 0.008333333767950534820556640625) * buffer.b1;
        _333 = (_333 + _MainTex.sample(_MainTexSmplr, fma(_206 * fma(-_217, 0.00999999977648258209228515625, 1.0), _204, float2(0.5)))) + _MainTex.sample(_MainTexSmplr, fma(_206 * fma(_217, 0.00999999977648258209228515625, 1.0), _204, float2(0.5)));
        _332++;
        continue;
    }
    float2 _155 = _115 / float2(buffer.s2);
    float2 _279 = _155 / _204;
    float4 _335;
    _335 = _MainTex.sample(_MainTexSmplr, (_155 + float2(0.5)));
    for (int _334 = 1; _334 <= 30; )
    {
        float _290 = (float(_334) * 0.008333333767950534820556640625) * buffer.b2;
        _335 = (_335 + _MainTex.sample(_MainTexSmplr, fma(_279 * fma(-_290, 0.00999999977648258209228515625, 1.0), _204, float2(0.5)))) + _MainTex.sample(_MainTexSmplr, fma(_279 * fma(_290, 0.00999999977648258209228515625, 1.0), _204, float2(0.5)));
        _334++;
        continue;
    }
    out.gl_FragColor = fma(_333, float4(0.0163934417068958282470703125), (_335 * float4(0.0163934417068958282470703125)) * buffer.a2);
    return out;
}

