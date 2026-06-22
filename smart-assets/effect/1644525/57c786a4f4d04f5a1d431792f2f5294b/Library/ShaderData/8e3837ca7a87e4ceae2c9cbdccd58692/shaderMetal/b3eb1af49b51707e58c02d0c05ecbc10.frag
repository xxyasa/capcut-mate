#include <metal_stdlib>
#include <simd/simd.h>

using namespace metal;

struct buffer_t
{
    int u_ANIMSEQ;
    float4 _MainTex_ST;
    float blurStep;
    int u_BLUR_TYPE;
    float u_OutputWidth;
    float u_OutputHeight;
    float2 blurDirection;
};

struct main0_out
{
    float4 gl_FragColor [[color(0)]];
};

struct main0_in
{
    float2 uv0 [[user(uv0)]];
};

fragment main0_out main0(main0_in in [[stage_in]], constant buffer_t& buffer, texture2d<float> _MainTex [[texture(0)]], sampler _MainTexSmplr [[sampler(0)]], float4 gl_FragCoord [[position]])
{
    main0_out out = {};
    float4 _501;
    if (buffer.u_BLUR_TYPE == 1)
    {
        float2 _309 = (float2(1.0) / float2(buffer.u_OutputWidth, buffer.u_OutputHeight)) * buffer.blurStep;
        float _312 = fast::max(length(buffer.blurDirection), 9.9999999747524270787835121154785e-07);
        float2 _516 = float2((buffer.blurDirection.x / _312) * _309.x, (buffer.blurDirection.y / _312) * _309.y);
        float4 _500;
        _500 = float4(0.0);
        float4 _365;
        for (int _499 = -7; _499 <= 7; _500 = _365, _499++)
        {
            float2 _341 = in.uv0 + (_516 * float(_499));
            float2 _503;
            if (buffer.u_ANIMSEQ == 1)
            {
                _503 = fma(float2(fast::clamp(_341.x, 0.0, 1.0), fast::clamp(_341.y, 0.0, 1.0)), buffer._MainTex_ST.xy, buffer._MainTex_ST.zw);
            }
            else
            {
                _503 = _341;
            }
            _365 = _500 + _MainTex.sample(_MainTexSmplr, _503);
        }
        _501 = _500 * float4(0.066666670143604278564453125);
    }
    else
    {
        float4 _502;
        if (buffer.u_BLUR_TYPE == 2)
        {
            float2 _388 = float2(0.5) - in.uv0;
            float _464 = fract(sin(dot(gl_FragCoord.xyz, float3(12.98980045318603515625, 78.233001708984375, 151.71820068359375))) * 43758.546875);
            float4 _493;
            float _494;
            _494 = 0.0;
            _493 = float4(0.0);
            float4 _439;
            float _442;
            for (int _492 = 0; _492 <= 25; _494 = _442, _493 = _439, _492++)
            {
                float _399 = (float(_492) + _464) - 0.5;
                float _400 = _399 * 0.039999999105930328369140625;
                float _405 = fma(_399, 0.039999999105930328369140625, -(_400 * _400));
                float2 _413 = in.uv0 + ((_388 * _400) * buffer.blurStep);
                float2 _495;
                if (buffer.u_ANIMSEQ == 1)
                {
                    _495 = fma(float2(fast::clamp(_413.x, 0.0, 1.0), fast::clamp(_413.y, 0.0, 1.0)), buffer._MainTex_ST.xy, buffer._MainTex_ST.zw);
                }
                else
                {
                    _495 = _413;
                }
                _439 = _493 + (_MainTex.sample(_MainTexSmplr, _495) * (4.0 * _405));
                _442 = fma(4.0, _405, _494);
            }
            _502 = _493 / float4(_494);
        }
        else
        {
            float2 _491;
            if (buffer.u_ANIMSEQ == 1)
            {
                _491 = fma(float2(fast::clamp(in.uv0.x, 0.0, 1.0), fast::clamp(in.uv0.y, 0.0, 1.0)), buffer._MainTex_ST.xy, buffer._MainTex_ST.zw);
            }
            else
            {
                _491 = in.uv0;
            }
            _502 = _MainTex.sample(_MainTexSmplr, _491);
        }
        _501 = _502;
    }
    out.gl_FragColor = _501;
    return out;
}

