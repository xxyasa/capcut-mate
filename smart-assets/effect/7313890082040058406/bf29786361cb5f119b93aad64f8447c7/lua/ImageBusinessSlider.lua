--write by editor  EffectSDK:15.1.0 EngineVersion:15.1.0 EditorBuildTime:Oct_14_2023_02_44_41
--sliderVersion: 20230517  Lua generation date: Thu Dec 14 20:09:58 2023


local exports = exports or {}
local ImageBusinessSlider = ImageBusinessSlider or {}
ImageBusinessSlider.__index = ImageBusinessSlider


function ImageBusinessSlider.new(construct, ...)
    local self = setmetatable({}, ImageBusinessSlider)
    if construct and ImageBusinessSlider.constructor then
        ImageBusinessSlider.constructor(self, ...)
    end
    return self
end


local function remap(x, a, b)
    return x * (b - a) + a
end


function ImageBusinessSlider:onStart(sys)
end


function ImageBusinessSlider:onEvent(sys,event)
end


exports.ImageBusinessSlider = ImageBusinessSlider
return exports