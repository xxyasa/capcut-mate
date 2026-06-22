local Utils = require("common/Utils")
local AETools = require("common/AETools")
local Helper = require("info_sticker/Helper")
local AE = require("AE")


local TextMain = {}
TextMain.__index = TextMain
function TextMain.new (env)
    local self = setmetatable({}, TextMain)
    self.ANIM_T = 23
    self.CHAR_DT = 2
    self.LINE_DT = 0.15
    self.AE = AE
    return self
end


function TextMain:onCreate (env)
    ---#ifdef DEV
--//    env.text.str = "consultly\nconsultly\nconsultly"
--//    env.text.typeSettingParam.typeSettingKind = Amaz.TypeSettingKind.HORIZONTAL
--//    Helper.setFontSize(env.text, 15)
--//    env.transparent = env.scene.assetMgr:SyncLoad("material/transparent.material")
    ---#endif

    self.aeP = AETools.new(self.AE.position)
    self.aeP:setAnimFrameRange(0, 24)
    self.aeS = AETools.new(self.AE.scale)
    self.aeS:setAnimFrameRange(0, 23)
end

function TextMain:onShow (env)
    local Text = env.text
    Text:forceTypeSetting()

    self.copy = Helper.attachCopy(Text.entity, "copy")
    self.copy.Text:forceTypeSetting()
    self.lines = Helper.splitByLine(self.copy.Text.letters)

    local maxLineDuration = 0
    local lastLineTime = 0
    local lastLineDelay = 0
    for _, line in ipairs(self.lines) do
        line.delay = lastLineDelay + lastLineTime * self.LINE_DT
        line.time = (#line-1) * self.CHAR_DT + self.ANIM_T
        maxLineDuration = math.max(maxLineDuration, line.delay + line.time)
        lastLineTime = line.time
        lastLineDelay = line.delay

        line.L = 99999999
        line.R = -99999999
        line.B = 99999999
        line.T = -99999999
        for _, char in ipairs(line) do
            local pos = char.initialPosition
            local size = char.rect
            line.L = math.min(line.L, pos.x - size.width * 0.5)
            line.R = math.max(line.R, pos.x + size.width * 0.5)
            line.B = math.min(line.B, pos.y - size.height * 0.5)
            line.T = math.max(line.T, pos.y + size.height * 0.5)
        end
        line.dX = math.abs(line.R - line.L) * 0.35
        line.dY = math.abs(line.T - line.B) * 0.35
        line.X0 = Utils.mix(line.L, line.R, 0.25)
        line.Y0 = Utils.mix(line.B, line.T, 0.25)
    end
    self.maxLineTime = maxLineDuration

    Helper.disableText(Text.entity, env.transparent)
end

function TextMain:onHide (env)
    local node = env.text.entity
    Helper.detachCopy(node, "copy")
    Helper.enableText(node)
end

function TextMain:onUpdate (env, elapsed)
    --elapsed = env.duration - elapsed
    local unitTime = env.duration / self.maxLineTime
    local charInterval = unitTime * self.CHAR_DT
    local animDuration = unitTime * self.ANIM_T
    local vertical = self.copy.Text.typeSettingParam.typeSettingKind == Amaz.TypeSettingKind.VERTICAL
    for _, line in ipairs(self.lines) do
        local lineStartTime = line.delay * unitTime
        local moveProgress = Utils.step(lineStartTime, lineStartTime + (line.time-12) * unitTime, elapsed)
        local dP = self.aeP:GetVal("Position", moveProgress)[1]
        dP = Utils.step(1000, 1361.5, dP)

        for i, char in ipairs(line) do
            local k = i - 1
            local charStartTime = lineStartTime + k * charInterval
            local charProgress = Utils.step(charStartTime, charStartTime + animDuration, elapsed)
            local s = self.aeS:GetVal("Scale", charProgress)[1] * 0.01
            char.scale = Amaz.Vector2f(s, s)
            local p0 = char.initialPosition

            if vertical then
                local x = line.X0 + (p0.x - line.X0) * s
                local y = p0.y - dP * line.dY
                char.position = Amaz.Vector2f(x, y)
            else
                local x = p0.x + dP * line.dX
                local y = line.Y0 + (p0.y - line.Y0) * s
                char.position = Amaz.Vector2f(x, y)
            end
        end
    end
end

return TextMain