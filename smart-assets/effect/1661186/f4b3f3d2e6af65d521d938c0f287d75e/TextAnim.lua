-- local util = nil ---@class Util
local util = {}     ---@class Util
local json = cjson.new()
local rootDir = nil
local record_t = {}

local function getBezierValue(controls, t)
    local ret = {}
    local xc1 = controls[1]
    local yc1 = controls[2]
    local xc2 = controls[3]
    local yc2 = controls[4]
    ret[1] = 3*xc1*(1-t)*(1-t)*t+3*xc2*(1-t)*t*t+t*t*t
    ret[2] = 3*yc1*(1-t)*(1-t)*t+3*yc2*(1-t)*t*t+t*t*t
    return ret
end

local function getBezierDerivative(controls, t)
    local ret = {}
    local xc1 = controls[1]
    local yc1 = controls[2]
    local xc2 = controls[3]
    local yc2 = controls[4]
    ret[1] = 3*xc1*(1-t)*(1-3*t)+3*xc2*(2-3*t)*t+3*t*t
    ret[2] = 3*yc1*(1-t)*(1-3*t)+3*yc2*(2-3*t)*t+3*t*t
    return ret
end

local function getBezierTfromX(controls, x)
    local ts = 0
    local te = 1
    -- divide and conque
    repeat
        local tm = (ts+te)/2
        local value = getBezierValue(controls, tm)
        if(value[1]>x) then
            te = tm
        else
            ts = tm
        end
    until(te-ts < 0.0001)

    return (te+ts)/2
end

local function changeVec2ToTable(val)
    return {val.x, val.y}
end

local function changeVec3ToTable(val)
    return {val.x, val.y, val.z}
end

local function changeVec4ToTable(val)
    return {val.x, val.y, val.z, val.w}
end

local function changeCol3ToTable(val)
    return {val.r, val.g, val.b}
end

local function changeCol4ToTable(val)
    return {val.r, val.g, val.b, val.a}
end

local function changeTable2Vec4(t)
    return Amaz.Vector4f(t[1], t[2], t[3], t[4])
end

local function changeTable2Vec3(t)
    return Amaz.Vector3f(t[1], t[2], t[3])
end

local function changeTable2Vec2(t)
    return Amaz.Vector2f(t[1], t[2])
end

local function changeTable2Col3(t)
    return Amaz.Color(t[1], t[2], t[3])
end

local function changeTable2Col4(t)
    return Amaz.Color(t[1], t[2], t[3], t[4])
end

local _typeSwitch = {
    ["vec4"] = function(v)
        return changeVec4ToTable(v)
    end,
    ["vec3"] = function(v)
        return changeVec3ToTable(v)
    end,
    ["vec2"] = function(v)
        return changeVec2ToTable(v)
    end,
    ["float"] = function(v)
        return tonumber(v)
    end,
    ["string"] = function(v)
        return tostring(v)
    end,
    ["col3"] = function(v)
        return changeCol3ToTable(v)
    end,
    ["col4"] = function(v)
        return changeCol4ToTable(v)
    end,

    -- change table to userdata
    ["_vec4"] = function(v)
        return changeTable2Vec4(v)
    end,
    ["_vec3"] = function(v)
        return changeTable2Vec3(v)
    end,
    ["_vec2"] = function(v)
        return changeTable2Vec2(v)
    end,
    ["_float"] = function(v)
        return tonumber(v)
    end,
    ["_string"] = function(v)
        return tostring(v)
    end,
    ["_col3"] = function(v)
        return changeTable2Col3(v)
    end,
    ["_col4"] = function(v)
        return changeTable2Col4(v)
    end,
}

local function typeSwitch()
    return _typeSwitch
end

local function createTableContent()
    -- Amaz.LOGI("lrc", "createTableContent")
    local t = {}
    for k,v in pairs(record_t) do
        t[k] = {}
        t[k]["type"] = v["type"]
        t[k]["val"] = v["func"](v["val"])
    end
    return t
end

function util.registerParams(_name, _data, _type)
    record_t[_name] = {
        ["type"] = _type,
        ["val"] = _data,
        ["func"] = _typeSwitch[_type]
    }
end

function util.getRegistedParams()
    return record_t
end

function util.setRegistedVal(_name, _data)
    record_t[_name]["val"] = _data
end

function util.getRootDir()
    if rootDir == nil then
        local str = debug.getinfo(2, "S").source
        rootDir = str:match("@?(.*/)")
    end
    Amaz.LOGI("lrc getRootDir 123", tostring(rootDir))
    return rootDir
end

function util.registerRootDir(path)
    rootDir = path
end

function util.bezier(controls)
    local control = controls
    if type(control) ~= "table" then
        control = changeVec4ToTable(controls)
    end
    return function (t, b, c, d)
        t = t/d
        local tvalue = getBezierTfromX(control, t)
        local value =  getBezierValue(control, tvalue)
        return b + c * value[2]
    end
end

function util.remap01(a,b,x)
    if x < a then return 0 end
    if x > b then return 1 end
    return (x-a)/(b-a)
end

function util.mix(a, b, x)
    return a * (1-x) + b * x
end

function util.CreateJsonFile(file_path)
    local t = createTableContent()
    local content = json.encode(t)
    local file = io.open(util.getRootDir()..file_path, "w+b")
    if file then
      file:write(tostring(content))
      io.close(file)
    end
end

function util.ReadFromJson(file_path)
    local file = io.input(util.getRootDir()..file_path)
    local json_data = json.decode(io.read("*a"))
    local res = {}
    for k, v in pairs(json_data) do
        local func = _typeSwitch["_"..tostring(v["type"])]
        res[k] = func(v["val"])
    end
    return res
end

function util.bezierWithParams(input_val_4, min_val, max_val, in_val, reverse)
    if type(input_val_4) == "tabke" then
        if reverse == nil then
            return util.bezier(input_val_4)(util.remap01(min_val, max_val, in_val), 0, 1, 1)
        else
            return util.bezier(input_val_4)(1-util.remap01(min_val, max_val, in_val), 0, 1, 1)
        end
    else
        if reverse == nil then
            return util.bezier(util.changeVec4ToTable(input_val_4))(util.remap01(min_val, max_val, in_val), 0, 1, 1)
        else
            return util.bezier(util.changeVec4ToTable(input_val_4))(1-util.remap01(min_val, max_val, in_val), 0, 1, 1)
        end
    end
end

function util.test()
    Amaz.LOGI("lrc", "test123")
end




local exports = exports or {}
local TextAnim = TextAnim or {}
TextAnim.__index = TextAnim
---@class TextAnim : ScriptComponent
---@field autoplay boolean
---@field isBlur boolean
---@field duration number
---@field curTime number
---@field progress number [UI(Range={0, 1}, Slider)]
---@field bezierValue1 Vector4f
---@field bezierValue2 Vector4f
---@field single_char_anim_time number [UI(Range={0, 1}, Slider)]
---@field bezierValue3 Vector4f
---@field textAnimTimer Vector2f
---@field initialPosition_weight number [UI(Range={0, 1}, Slider)]
---@field fade_info Vector2f
---@field blur_info Vector4f

local function print(f,b)
    Amaz.LOGI("lrc "..tostring(f), tostring(b))
end

local function getRootDir()
    local rootDir = nil
    if rootDir == nil then
        local str = debug.getinfo(2, "S").source
        rootDir = str:match("@?(.*/)")
    end
    return rootDir
end

function TextAnim.new(construct, ...)
    local self = setmetatable({}, TextAnim)

    -- online attr
    self.duration = 0
    self.curTime = 0

    self.sharedMaterial = nil
	self.materials = nil
    self.renderer = nil
    self.isVertical = 0.0
    self.first = true

    -- Editor about ---
    self.autoplay = false
    self.isBlur = true
    self.duration = 2

    -- Runtime ---
    self.progress = 0

    -- Init Attr ----
    self.bezierValue1 = Amaz.Vector4f(.16, .81, .44, 1)
    self.bezierValue2 = Amaz.Vector4f(.16, .81, .44, 1)
    self.bezierValue3 = Amaz.Vector4f(.16, .81, .44, 1)
    self.textAnimTimer = Amaz.Vector2f(0, 0.1)
    self.single_char_anim_time = 0.5
    self.initialPosition_weight = 0.5
    self.fade_info = Amaz.Vector2f(0, 0.2)
    self.blur_info = Amaz.Vector4f(0, 0.3, 0, 0.2)

    self:registerParams("bezierValue1", "vec4")
    self:registerParams("bezierValue2", "vec4")
    self:registerParams("bezierValue3", "vec4")
    self:registerParams("textAnimTimer", "vec2")
    self:registerParams("initialPosition_weight", "float")
    self:registerParams("single_char_anim_time", "float")
    self:registerParams("fade_info", "vec2")
    self:registerParams("blur_info", "vec4")

    if construct and TextAnim.constructor then TextAnim.constructor(self, ...) end
    return self
end

function TextAnim:registerParams(_name, _type)
    local _data = self[_name]
    -- if util == nil then
        -- util = includeRelativePath("Util")
        util.registerRootDir(getRootDir())
    -- end
    util.registerParams(_name, _data, _type)
end

function TextAnim:constructor()

end

function TextAnim:transInitial(trans)
    if trans then
        trans.localPosition = Amaz.Vector3f(0,0,0)
        trans.localScale = Amaz.Vector3f(1,1,1)
        trans.localEulerAngle = Amaz.Vector3f(0,0,0)
    end
end

function TextAnim:textInitial(text)
    if text then
        for i = 1, text.chars:size() do
            local char = text.chars:get(i-1)
            char.position = char.initialPosition
        end
    end
end

function TextAnim:onStart(comp) 
    -- if util == nil then
        -- util = includeRelativePath("Util")
        util.registerRootDir(getRootDir())
    -- end

    self.entity = comp.entity
	self.text = comp.entity:getComponent("SDFText")
    if self.text == nil then
        local text = comp.entity:getComponent('Text')
        if text ~= nil then
			self.text = comp.entity:addComponent('SDFText')
            self.text:setTextWrapper(text)
        end
    end
    self.trans = comp.entity:getComponent("Transform")
	self.transParent = self.trans.parent

    self.renderer = nil
	if self.text ~= nil then
		self.renderer = comp.entity:getComponent("MeshRenderer")
	else
		self.renderer = comp.entity:getComponent("Sprite2DRenderer")
	end

    self:transInitial(self.trans)

    self.first = true

end

function TextAnim:initAnim()
    self.text.renderToRT = true
    local materials = Amaz.Vector()
    local InsMaterials = nil
    if self.sharedMaterial then
        InsMaterials = self.sharedMaterial:instantiate()
    else
        InsMaterials = self.renderer.material
    end
    materials:pushBack(InsMaterials)
    self.materials = materials
    self.renderer.materials = self.materials

    if Amaz.Macros and Amaz.Macros.EditorSDK then
    else
        self:ReadFromJson()
    end
    -- self.text.renderToRT = true

    local rect = self.text.rect
    local w = Amaz.BuiltinObject.getOutputTextureWidth()
    local h = Amaz.BuiltinObject.getOutputTextureHeight()

    self.char_info_table = {}

    if self.text then

        if self.text.typeSettingKind == 1 then
            for i = self.text.chars:size(), 1, -1 do
                local char = self.text.chars:get(i-1)
                if char.utf8code ~= '\n' then
                    local rowth = char.rowth + 1
                    if self.char_info_table[rowth] == nil then
                        self.char_info_table[rowth] = {}
                    end
                    self.char_info_table[rowth][#self.char_info_table[rowth]+1] = char
                end
            end
        else
            for i = 1, self.text.chars:size() do
                local char = self.text.chars:get(i-1)
                if char.utf8code ~= '\n' then
                    local rowth = char.rowth + 1
                    if self.char_info_table[rowth] == nil then
                        self.char_info_table[rowth] = {}
                    end
                    self.char_info_table[rowth][#self.char_info_table[rowth]+1] = char
                end
            end
        end
    end

    -- self.curve = includeRelativePath("AETools"):new(util)
    -- self.curve:addKeyFrameInfo({0, 16.6666}, {-0.0007, 57.2604}, 0, 77)
    -- self.curve:addKeyFrameInfo({-0.00011, 17.9937}, {-0.0008, 25.363}, 4, -24)
    -- self.curve:addKeyFrameInfo({-0.0003, 47.846}, {0, 33.3333}, 7, 10)
    -- self.curve:addKeyFrameInfo({-130.99888, 71.97468}, {-133.34241, 20.18391}, 9, -4)
    -- self.curve:addKeyFrameInfo({0, 40.75513}, {-0.0007, 4.30777}, 11, 1)
    -- self.curve:addKeyFrameInfo({-0.0007, 32.09104}, {0, 0.01}, 12.5, 0)
end

function TextAnim:onUpdate(comp, time)
    if Amaz.Macros and Amaz.Macros.EditorSDK then
        self.curTime = self.curTime + time
        self:seek(self.curTime)
    end
end

---@function [UI(Button="generate json file")]
function TextAnim:CreateJsonFile()
    Amaz.LOGI("lrc", "CreateJsonFile")

    for k,v in pairs(util.getRegistedParams()) do
        if self[k] == nil then
            Amaz.LOGE("lrc ERROR!!!", "no registed value called : "..tostring(k))
        else
            util.setRegistedVal(k, self[k])
        end
    end
    util.CreateJsonFile("data_val.json")
end

---@function [UI(Button="read from json file")]
function TextAnim:ReadFromJson()
    Amaz.LOGI("lrc readfrom json", "read from json")
    local t = util.ReadFromJson("data_val.json")
    for k,v in pairs(t) do 
        self[k] = v
    end
end

function TextAnim:seek(time)
    if self.first and self.text.chars:size() > 0 then
        self:initAnim()
        self.first = false
    end


    if Amaz.Macros and Amaz.Macros.EditorSDK then
        if self.autoplay then
            self.progress = time % self.duration / self.duration
        end
    else
        self.progress = time % (self.duration+0.001) / self.duration
        self.isBlur = true
    end

    if self.text and self.text.chars:size() > 0 then

        local rect = self.text.rect

        if Amaz.Macros and Amaz.Macros.EditorSDK then
        else
        end

        -- self.text.targetRTExtraSize = Amaz.Vector2f(rect.width, 0)

        for line, chars in pairs(self.char_info_table) do
            local size = #chars
            local bezier1 = self.bezierValue1
            local bezier2 = self.bezierValue2
            local bezier3 = self.bezierValue3
            local _progress = util.remap01(self.textAnimTimer.x, self.textAnimTimer.y, self.progress)

            -- Amaz.LOGI("lrc", self.text.typeSettingKind)
            if self.text.typeSettingKind == 1 then
                -- vertical type setting
                for i = 1, #chars do
                    local char = chars[i]
                    local init_pos = char.initialPosition
    
                    local start_timer = util.mix(0, 1-self.single_char_anim_time, (size-i)/size)
                    local end_timer = util.mix(self.single_char_anim_time, 1, (size-i)/size)
                    local progress = util.remap01(start_timer, end_timer, _progress)
    
                    local i_bezier = util.bezier({bezier3.x, bezier3.y, bezier3.z, bezier3.w})((i)/size, 0, 1, 1)
                    local pos_y = util.mix(
                        init_pos.y - rect.height * (1-self.initialPosition_weight),
                        init_pos.y,
                        util.bezier({
                            util.mix(bezier1.x, bezier2.x, i_bezier), 
                            util.mix(bezier1.y, bezier2.y, i_bezier),
                            util.mix(bezier1.z, bezier2.z, i_bezier),
                            util.mix(bezier1.w, bezier2.w, i_bezier)}
                        )(progress, 0, 1, 1)
                    )
                    char.position = Amaz.Vector3f(init_pos.x, pos_y, init_pos.z)
                end

            else
                -- horizontal type setting

                for i = 1, #chars do
                    --- 1 for right, size for left
                    local char = chars[i]
                    local init_pos = char.initialPosition
                    -- Amaz.LOGI(char.idInRow.." lrc "..char.utf8code, char.rowth)
    
                    local start_timer = util.mix(0, 1-self.single_char_anim_time, (size-i)/size)
                    local end_timer = util.mix(self.single_char_anim_time, 1, (size-i)/size)
                    local progress = util.remap01(start_timer, end_timer, _progress)
    
                    local i_bezier = util.bezier({bezier3.x, bezier3.y, bezier3.z, bezier3.w})((i)/size, 0, 1, 1)
                    local pos_x = util.mix(
                        init_pos.x - rect.width * (1-self.initialPosition_weight),
                        init_pos.x,
                        util.bezier({
                            util.mix(bezier1.x, bezier2.x, i_bezier), 
                            util.mix(bezier1.y, bezier2.y, i_bezier),
                            util.mix(bezier1.z, bezier2.z, i_bezier),
                            util.mix(bezier1.w, bezier2.w, i_bezier)}
                        )(progress, 0, 1, 1)
                    )
                    char.position = Amaz.Vector3f(pos_x, init_pos.y, init_pos.z)
                end

            end
        end

        -- local col = self.text.textColor
        if self.isBlur then
            local fade_val = util.remap01(self.fade_info.x, self.fade_info.y, self.progress)
            self.materials:get(0):setFloat("fade_val", fade_val)
            -- self.text.textColor = Amaz.Vector4f(col.x, col.y, col.z, fade_val)
            self.materials:get(0):setVec2("blur_val", 
                Amaz.Vector2f(self.blur_info.x, (1-util.remap01(self.blur_info.z, self.blur_info.w, self.progress)) * self.blur_info.y))
        else
            -- self.text.textColor = Amaz.Vector4f(col.x, col.y, col.z, 1)
            self.materials:get(0):setVec2("blur_val", Amaz.Vector2f(0,0))
            self.materials:get(0):setVec2("fade_val", 1)
        end
        self.materials:get(0):setFloat("typeSettingKind", self.text.typeSettingKind == 1 and 1 or 0)


    end

end

function TextAnim:resetData()
    if self.text and self.text.chars:size() > 0 then

        self:transInitial(self.trans)
        self:textInitial(self.text)

        -- self.materials:get(0):setFloat("fade", 1)
        -- self.materials:get(0):setFloat("progress", 0)
        -- self.materials:get(0):setFloat("isBlur", 0)
        -- self.materials:get(0):setFloat("blurStep", 0)
        self.text.renderToRT = false
        self.text.targetRTExtraSize = Amaz.Vector2f(0,0)
    end
end


function TextAnim:setDuration(duration)
    self.duration = duration
end

function TextAnim:clear()
    EffectSdk.LOG_LEVEL(8, "lrc ========>>:clear")
    self:resetData()
end


function TextAnim:onEnter()
    self:resetData()
    self.first = true
end

function TextAnim:onLeave()
    EffectSdk.LOG_LEVEL(8, "lrc ========>>:onleave")
    self:resetData()
    self.first = true
end

exports.TextAnim = TextAnim
return exports
