local Utils = require("common/Utils")
local AEAdapter = require("common/AEAdapter")
local Helper = require("info_sticker/Helper")
local AE = require("AE")

local CHAR_INTERVAL = 3 / 30
local CHAR_DURATION = 33 / 30
--local FADE_DURATION = 19 / 30
--local FONT_SIZE = 120
--local CHAR_POSITION_X = 188.7
--local CHAR_POSITION_Y = 290


local TextMain = {}
TextMain.__index = TextMain
function TextMain.new ()
    return setmetatable({}, TextMain)
end

function TextMain:onCreate (env)
    self.ae = AEAdapter:new()
    self.ae:addKeyframes("char", AE)

    ---#ifdef DEV
--//    env.rootTextOld.fontSize = 14
--//    env.rootTextOld.str = "First Line\nSecond Line"
    ---#endif
end

function TextMain:onShow (env)
end

function TextMain:onHide (env)
    local sdf = env.rootTextOld
    local chars = sdf.chars
    for i = 0, chars:size() - 1 do
        local char = chars:get(i)
        char.position = char.initialPosition:copy()
        char.color = Amaz.Vector4f(1, 1, 1, 1)
        char.anchor = Amaz.Vector2f(0, 0)
        char.rotate = Amaz.Vector3f(0, 0, 0)
        char.scale = Amaz.Vector3f(1, 1, 1)
    end
end

function TextMain:onChange (env)
    local text = env.rootTextOld
    text:forceTypeSetting()
    self.chars = Helper.splitByChar(text.chars)
    for i = 1, #self.chars do
        for j = 1, #self.chars[i] do
            local char = self.chars[i][j]
            char.anchor = Amaz.Vector2f(0, -0.3 * char.height)
            char.rotate = Amaz.Vector3f(0, 0, 0)
        end
    end
end

function TextMain:onUpdate (env, elapsed)
    if not self.chars or #self.chars <= 0 then
        return
    end

    --elapsed = env.duration - elapsed
    local n = #self.chars
    local t = CHAR_INTERVAL * (n - 1) + CHAR_DURATION
    local k = env.duration / t

    local time = elapsed / env.duration * t
    for i = 1, #self.chars do
        local char = self.chars[i][1]
        local from = (i - 1) * CHAR_INTERVAL
        local to = from + CHAR_DURATION

        local pos = char.initialPosition:copy()
        if time <= from then
            char.scale = Amaz.Vector3f(0, 0, 0)
        elseif time >= to then
            char.scale = Amaz.Vector3f(1, 1, 1)
            char.color = Amaz.Vector4f(1, 1, 1, 1)
            char.rotate = Amaz.Vector3f(0, 0, 0)
            char.position = pos
        else
            local progress = (time - from) / (to - from)

            local scale = self.ae:get("char/ADBE Scale", progress * CHAR_DURATION)[1] * 0.01
            local alpha = self.ae:get("char/ADBE Opacity", progress * CHAR_DURATION)[1] * 0.01
            local z = self.ae:get("char/ADBE Rotate Z", progress * CHAR_DURATION)[1]

            char.scale = Amaz.Vector3f(scale, scale, scale)
            char.color = Amaz.Vector4f(1, 1, 1, alpha)
            char.rotate = Amaz.Vector3f(0, 0, -z)

            pos.y = pos.y + char.height * 0.3 * (scale - 1)
            char.position = pos
        end
    end
end

return TextMain