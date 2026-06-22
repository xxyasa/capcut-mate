local TextMain = require("TextMain")


local TextAnim = {}
TextAnim.__index = TextAnim


function TextAnim.new ()
    local self = setmetatable({}, TextAnim)
    self._main = TextMain.new(self)
    return self
end

function TextAnim:onStart (comp)
    self.curTime = 0.0
    self.duration = 5.0
    self._visible = false

    self.scene = comp.entity.scene
    self.path = debug.getinfo(1, "S").source:match("@?(.*/)")
    self.node = comp.entity:getComponent("Transform")
    self.text = comp.entity:getComponent("Text")
    self._main:onCreate(self)
end

function TextAnim:onEnter ()
    if not self.visible then
        self._main:onShow(self)
        self._visible = true
    end
end

function TextAnim:onLeave ()
    if self._visible then
        self._main:onHide(self)
        self._visible = false
    end
    collectgarbage("collect")
end

function TextAnim:clear ()
    self:onLeave()
end

function TextAnim:setDuration (duration)
    self.duration = duration
end

function TextAnim:seek (time)
    if self._visible then
        self._main:onUpdate(self, time)
    end
end


---#ifdef DEV
--//function TextAnim:onUpdate (comp, dt)
--//    self:seek(self.seekTime or self.curTime)
--//    self.curTime = self.curTime + dt
--//end
--//function TextAnim:onEvent (comp, event)
--//    if event.type ~= Amaz.EventType.TOUCH then
--//        return
--//    end
--//    local pointer = event.args:get(0)
--//    if pointer.type == Amaz.TouchType.TOUCH_BEGAN then
--//        self.curTime = 0
--//        self:onEnter()
--//    elseif pointer.type == Amaz.TouchType.TOUCH_MOVED then
--//        self.seekTime = pointer.x * self.duration
--//    elseif pointer.type == Amaz.TouchType.TOUCH_ENDED or pointer.type == Amaz.TouchType.TOUCH_CANCELLED then
--//        self.seekTime = nil
--//        self:onLeave()
--//    end
--//end
---#endif


local exports = exports or {}
exports.TextAnim = TextAnim
return exports