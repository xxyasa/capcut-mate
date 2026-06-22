#define AE_AreaLightNum 0
#define AE_DirLightNum 0
#define AE_PointLightNum 0
#define AE_SpotLightNum 0
attribute vec4 position;
attribute vec2 texcoord0;
varying vec2 uv0;
uniform mat4 u_MVP;

uniform mat4 u_VP;

void main()
{
    vec4 newPos = position;
    gl_Position = u_MVP * newPos;
    uv0 = texcoord0;
    uv0.y = 1.0 - uv0.y;
}
