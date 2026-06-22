




---------- common/Utils.lua ----------
local Utils = {}



-- System
---@param fmt string
---@vararg any
function Utils.log (fmt, ...)
    ---#ifdef DEV
--//    local args = { ... }
--//    for i, v in ipairs(args) do
--//        local type = type(v)
--//        if type == "table" then
--//            args[i] = cjson.encode(v)
--//        elseif type == "number" then
--//            args[i] = v
--//        else
--//            args[i] = tostring(v)
--//        end
--//    end
--//    if Editor then
--//        Amaz.LOGW("MoreFive", string.format(fmt, unpack(args)))
--//    elseif EffectSdk then
--//        EffectSdk.LOG_LEVEL(8, string.format(fmt, unpack(args)))
--//    end
    ---#endif
end



-- Container
---@param src table
---@return table
function Utils.table_clone (src)
    if not src then
        return src
    end
    local dst = {}
    for k, v in pairs(src) do
        dst[k] = type(v) == "table" and Utils.clone(v) or v
    end
    return dst
end
---@param src any[]
---@param si number|nil
---@param ei number|nil
---@return any[]
function Utils.table_slice (src, si, ei)
    si = si or 1
    ei = ei or #src
    local dst = {}
    for i = si, ei do
        table.insert(dst, src[i])
    end
    return dst
end
---@vararg any[]
---@return any[]
function Utils.array_concat(...)
    local dst = {}
    for _, src in ipairs({...}) do
        for _, ele in ipairs(src) do
            table.insert(dst, ele)
        end
    end
    return dst
end
---@param src any[]
---@return any[]
function Utils.array_shuffle (src)
    local dst = {}
    if type(src) == "number" then
        for i = 1, src do
            dst[i] = i
        end
    else
        for i, v in ipairs(src) do
            dst[i] = v
        end
    end
    for n = #dst, 1, -1 do
        local i = math.floor(math.random(n))
        local v = dst[i]
        dst[i] = dst[n]
        dst[n] = v
    end
    return dst
end



-- Math
function Utils.clamp (value, min, max)
    return math.min(math.max(min, value), max)
end
function Utils.mix (x, y, a)
    return x + (y - x) * a
end
function Utils.step (edge0, edge1, value)
    return math.min(math.max(0, (value - edge0) / (edge1 - edge0)), 1)
end
function Utils.linearstep (edge0, edge1, value)
    return math.min(math.max(0, (value - edge0) / (edge1 - edge0)), 1)
end
function Utils.smoothstep (edge0, edge1, value)
    local t = math.min(math.max(0, (value - edge0) / (edge1 - edge0)), 1)
    return t * t * (3 - t - t)
end
function Utils.mirror (range, value)
    local round = value / range
    local roundF = 1 - math.abs(round % 2 - 1)
    local roundI = math.floor(round)
    return roundF, roundI
end
function Utils.bezier4 (q, x1, x2, x3, x4, y1, y2, y3, y4)
    local p = 1 - q
    local p2 = p * p
    local p3 = p2 * p
    local q2 = q * q
    local q3 = q2 * q
    local x = x1*p3 + 3*x2*p2*q + 3*x3*p*q2 + x4*q3
    local y = y4 and y1*p3 + 3*y2*p2*q + 3*y3*p*q2 + y4*q3
    return x, y
end
function Utils.bezier4x2y (x1, x2, x3, x4, y1, y2, y3, y4, x)
    local t_ = 0
    local _t = 1
    local bezier4 = Utils.bezier4
    repeat
        local _t_ = (t_ + _t) * 0.5
        local _x_ = bezier4(_t_, x1, x2, x3, x4)
        if _x_ > x then
            _t = _t_
        else
            t_ = _t_
        end
    until _t - t_ < 0.0078125

    local t = (t_ + _t) * 0.5
    return bezier4(t, y1, y2, y3, y4)
end



-- Easing
function Utils.sineIn (t)
    return 1 - math.cos(math.pi * t * .5)
end
function Utils.sineOut (t)
    return math.sin(math.pi * t * .5)
end
function Utils.sineInOut (t)
    return -(math.cos(math.pi * t) - 1) * .5
end
function Utils.quadIn (t)
    return t * t
end
function Utils.quadOut (t)
    return (2 - t) * t
end
function Utils.quadInOut (t)
    return t < .5 and 2 * t * t or t * (4 - t - t) - 1
end
function Utils.cubicIn (t)
    return t * t * t
end
function Utils.cubicOut (t)
    t = 1 - t
    return 1 - t * t * t
end
function Utils.cubicInOut (t)
    if t < .5 then
        return 4 * t * t * t
    else
        t = 2 - t - t
        return 1 - t * t * t * .5
    end
end
function Utils.quartIn (t)
    t = t * t
    return t * t
end
function Utils.quartOut (t)
    t = 1 - t
    t = t * t
    return 1 - t * t
end
function Utils.quartInOut (t)
    if t < .5 then
        t = t * t
        return 8 * t * t
    else
        t = 2 - t - t
        t = t * t
        return 1 - t * t * .5
    end
end
function Utils.expoIn (t)
    return t ~= 0 and math.pow(2, 10 - t - 10) or 0
end
function Utils.expoOut (t)
    return t ~= 1 and 1 - math.pow(2, -10 * t) or 1
end
function Utils.expoInOut (t)
    if t == 0 then
        return 0
    elseif t == 1 then
        return 1
    elseif t < .5 then
        return math.pow(2, 20 * t - 10) * .5
    else
        return 1 - math.pow(2, -20 * t + 10) * .5
    end
end
function Utils.circIn (t) return 1 - math.sqrt(1 - t * t) end
function Utils.circOut (t)
    t = t - 1
    return math.sqrt(1 - t * t)
end
function Utils.circInOut (t)
    if t < .5 then
        return .5 - math.sqrt(1 - 4 * t * t) * .5
    else
        t = 2 - t - t
        return .5 + math.sqrt(1 - t * t) * 0.5
    end
end
function Utils.backIn (t)
    local tt = t * t
    return 2.70158 * tt * t - 1.70158 * tt
end
function Utils.backOut (t)
    t = t - 1
    local tt = t * t
    return 1 + 2.70158 * tt * t + 1.70158 * tt
end
function Utils.backInOut (t)
    if t < .5 then
        t = t + t
        return (t * t * (3.5949095 * t - 2.5949095)) * .5
    else
        t = t + t - 2
        return (t * t * (3.5949095 * t + 2.5949095) + 2) * .5
    end
end
function Utils.elasticIn (t)
    if t == 0 then
        return 0
    elseif t == 1 then
        return 1
    else
        return -math.pow(2, 10 * t - 10) * math.sin((t * 10 - 10.75) * math.pi * 2 / 3)
    end
end
function Utils.elasticOut (t)
    if t == 0 then
        return 0
    elseif t == 1 then
        return 1
    else
        return math.pow(2, -10 * t) * math.sin((t * 10 - .75) * math.pi * 2 / 3) + 1
    end
end
function Utils.elasticInOut (t)
    if t == 0 then
        return 0
    elseif t == 1 then
        return 1
    elseif t < 0.5 then
        return -(math.pow(2, 20 * t - 10) * math.sin((t * 20 - 11.125) * math.pi * 2 / 4.5)) * .5
    else
        return (math.pow(2, -20 * t + 10) * math.sin((t * 20 - 11.125) * math.pi * 2 / 4.5)) * .5 + 1
    end
end
function Utils.bounceIn (t)
    return 1 - Utils.bounceOut(1 - t)
end
function Utils.bounceOut (t)
    local n1 = 7.5625;
    local d1 = 2.75;
    if t < 1 / d1 then
        return n1 * t * t;
    elseif t < 2 / d1 then
        t = t - 1.5 / d1
        return n1 * t * t + .75;
    elseif t < 2.5 / d1 then
        t = t - 2.25 / d1
        return n1 * t * t + .9375;
    else
        t = t - 2.625 / d1
        return n1 * t * t + .984375;
    end
end
function Utils.bounceInOut (t)
    if t < .5 then
        return (1 - Utils.bounceOut(1 - t + t)) * .5
    else
        return (1 + Utils.bounceOut(t + t - 1)) * .5
    end
end



-- Convert
---@param arr number[]
---@param si number
---@param ei number
---@return number|Vector2f|Vector3f|Vector4f
function Utils.arr2vec (arr, si, ei)
    si = si or 1
    ei = ei or #arr
    if si == ei then
        return arr[si]
    end
    local n = ei - si + 1
    if n == 3 then
        return Amaz.Vector3f(arr[si], arr[si + 1], arr[si + 2])
    elseif n == 2 then
        return Amaz.Vector2f(arr[si], arr[si + 1])
    elseif n == 4 then
        return Amaz.Vector4f(arr[si], arr[si + 1], arr[si + 2], arr[si + 3])
    end
end
function Utils.rgb2hsl (R, G, B)
    B = B or R.z
    G = G or R.y
    R = B and R or R.x
    local H, S, L;
    local max = math.max(R, G, B);
    local min = math.min(R, G, B);
    local delta = max - min

    L = (max + min) * 0.5
    S = delta == 0 and 0 or 1 - math.abs(L + L - 1)

    if delta == 0 then
        H = 0
    elseif max == R then
        H = (G - B) / delta % 6
    elseif max == G then
        H = (B - R) / delta + 2
    else
        H = (R - G) / delta + 4
    end
    H = H / 6

    if B then
        return H, S, L
    else
        return Amaz.Vector3f(H, S, L)
    end
end
function Utils.hsl2rgb (H, S, L)
    L = L or H.z
    S = S or H.y
    H = L and H or H.x
    H = H * 360
    local R, G, B
    local C = (1 - math.abs(L + L - 1)) * S
    local X = C * (1 - math.abs((H / 60) % 2 - 1))
    local m = L - C * 0.5

    if H < 60 then
        R, G, B = C, X, 0
    elseif H < 120 then
        R, G, B = X, C, 0
    elseif H < 180 then
        R, G, B = 0, C, X
    elseif H < 240 then
        R, G, B = 0, X, C
    elseif H < 300 then
        R, G, B = X, 0, C
    else
        R, G, B = C, 0, X
    end

    R = R + m
    G = G + m
    B = B + m

    if L then
        return R, G, B
    else
        return Amaz.Vector3f(R, G, B)
    end
end
function Utils.hueShift (R, G, B, shift)
    local H, S, L = Utils.rgb2hsl(R, G, B)
    H = H + shift
    R, G, B = Utils.hsl2rgb(H, S, L)
    return Amaz.Vector3f(R, G, B)
end



---@param range number
---@param step number
---@return number, number
function Utils.solveSamples (range, step)
    local samples = math.ceil(range / step)
    step = range / (samples + 0.1)
    return samples, step
end



-- String
function Utils.startswith (str, prefix)
    local n0 = string.len(str)
    local n1 = string.len(prefix)
    return n0 >= n1 and string.sub(str, 1, n1) == prefix
end
function Utils.endswith (str, suffix)
    local n0 = string.len(str)
    local n1 = string.len(suffix)
    return n0 > n1 and string.sub(str, n0 - n1 + 1, n0) == suffix
end
function Utils.trim (str, mode)
    local si = 1
    local ei = #str
    mode = mode or 0
    if mode >= 0 then
        while si <= ei and string.byte(str, si) <= 32 do
            si = si + 1
        end
    end
    if mode <= 0 then
        while ei > si and string.byte(str, ei) <= 32 do
            ei = ei - 1
        end
    end
    if si ~= 1 or ei ~= #str then
        return string.sub(str, si, ei)
    else
        return str
    end
end



-- UTF-8
---@param lead number
---@return number
function Utils.ucs4_size (lead)
    if lead < 128 then
        return 1
    elseif lead < 192 then
        return 0
    elseif lead < 224 then
        return 2
    elseif lead < 240 then
        return 3
    elseif lead < 248 then
        return 4
    elseif lead < 252 then
        return 5
    else
        return 6
    end
end
---@param str string
---@return number
function Utils.utf8_len (str)
    local n = #str
    local i = 1
    local l = 0
    while i <= n do
        local bytes = Utils.ucs4_size(string.byte(str, i))
        if bytes > 0 then
            i = i + bytes
            l = l + 1
        else
            i = i + 1
        end
    end
    return l
end
---@param str string
---@param si number|nil
---@param ei number|nil
---@return string
function Utils.utf8_sub (str, si, ei)
    local n = #str
    si = si or 1
    ei = ei or n
    ei = ei - si
    local i = 1
    while i <= n and si > 1 do
        local bytes = Utils.ucs4_size(string.byte(str, i))
        i = i + (bytes > 0 and bytes or 1)
        si = si - 1
    end
    local j = i
    while j <= n and ei > 0 do
        local bytes = Utils.ucs4_size(string.byte(str, j))
        j = j + (bytes > 0 and bytes or 1)
        ei = ei - 1
    end
    return string.sub(str, i, j)
end
---@param str string
---@param cb fun(str: string, index: number, size: number): boolean
function Utils.utf8_for (str, cb)
    local n = #str
    local i = 1
    while i <= n do
        local code = string.byte(str, i)
        local bytes = Utils.ucs4_size(code)
        if bytes > 0 then
            if cb(i, bytes, code) then
                return
            end
            i = i + bytes
        else
            i = i + 1
        end
    end
end



-- Size Fit
---@param dstSize Vector2f
---@param srcSizeOrAspect Vector2f|number
---@return Vector2f
function Utils.sizeFill (dstSize, srcSizeOrAspect)
    return dstSize:copy()
end
---@param dstSize Vector2f
---@param srcSizeOrAspect Vector2f|number
---@return Vector2f
function Utils.sizeFitX (dstSize, srcSizeOrAspect)
    srcSizeOrAspect = type(srcSizeOrAspect) == "number" and srcSizeOrAspect or srcSizeOrAspect.x / srcSizeOrAspect.y
    return Amaz.Vector2f(dstSize.x, dstSize.x / srcSizeOrAspect)
end
---@param dstSize Vector2f
---@param srcSizeOrAspect Vector2f|number
---@return Vector2f
function Utils.sizeFitY (dstSize, srcSizeOrAspect)
    srcSizeOrAspect = type(srcSizeOrAspect) == "number" and srcSizeOrAspect or srcSizeOrAspect.x / srcSizeOrAspect.y
    return Amaz.Vector2f(dstSize.y * srcSizeOrAspect, dstSize.y)
end
---@param dstSize Vector2f
---@param srcSizeOrAspect Vector2f|number
---@return Vector2f
function Utils.sizeContains (dstSize, srcSizeOrAspect)
    srcSizeOrAspect = type(srcSizeOrAspect) == "number" and srcSizeOrAspect or srcSizeOrAspect.x / srcSizeOrAspect.y
    return Amaz.Vector2f(math.min(dstSize.x, dstSize.y * srcSizeOrAspect), math.min(dstSize.x / srcSizeOrAspect, dstSize.y))
end
---@param dstSize Vector2f
---@param srcSizeOrAspect Vector2f|number
---@return Vector2f
function Utils.sizeCover (dstSize, srcSizeOrAspect)
    srcSizeOrAspect = type(srcSizeOrAspect) == "number" and srcSizeOrAspect or srcSizeOrAspect.x / srcSizeOrAspect.y
    return Amaz.Vector2f(math.max(dstSize.x, dstSize.y * srcSizeOrAspect), math.max(dstSize.x / srcSizeOrAspect, dstSize.y))
end








---------- common/AETools.lua ----------
local AETools = AETools or {}
AETools.__index = AETools

local function deepcopy(orig)
    local copy
    if type(orig) == "table" then
        copy = {}
        for orig_key, orig_value in next, orig, nil do
            copy[deepcopy(orig_key)] = deepcopy(orig_value)
        end
        -- setmetatable(copy, deepcopy(getmetatable(orig)))
    else
        copy = orig
    end
    return copy
end

function AETools.new(attrs)
    local self = setmetatable({}, AETools)
    self.attrs = attrs

    self:_init(100000, 0, true)

    return self
end

function AETools:_init(_min_frame, _max_frame, _auto_flag)
    local max_frame = _max_frame
    local min_frame = _min_frame
    for _,v in pairs(self.attrs) do
        for i = 1, #v do
            local content = v[i]
            if _auto_flag then
                local cur_frame_min = content[2][1]
                local cur_frame_max = content[2][2]
                max_frame = math.max(cur_frame_max, max_frame)
                min_frame = math.min(cur_frame_min, min_frame)
            end

            if content[4] ~= nil and content[5] ~= nil and (content[4][1] == 6413 or content[4][1] == 6415) and content[5][1] == 0 then
                local p0 = content[3][1]
                local totalLen = 0
                local lenInfo = {}
                lenInfo[0] = 0
                for test=1,200,1 do
                    local coord = self._cubicBezier3D(content[3][1], content[3][3], content[3][4], content[3][2], test/200)
                    local length = math.sqrt((coord[1]-p0[1])*(coord[1]-p0[1])+(coord[2]-p0[2])*(coord[2]-p0[2]))
                    p0 = coord
                    totalLen = totalLen + length
                    lenInfo[test] = totalLen
                    -- print(test/200 .. " coord: "..coord[1].." - "..coord[2])
                end
                for test=1,200,1 do
                    lenInfo[test] = lenInfo[test]/(lenInfo[200]+0.000001)
                    -- print(test/200 .. "  "..lenInfo[test])
                end
                content['lenInfo'] = lenInfo
            end
        end
    end

    self.all_frame = max_frame - min_frame
    self.min_frame = min_frame
end

function AETools:setAnimFrameRange(_min_frame, _max_frame)
    self:_init(_min_frame, _max_frame)
end

function AETools:getCurrFrameIndex(_p)
    local frame = math.floor(_p*self.all_frame)
    return frame + self.min_frame
end

function AETools:getFrameCount()
    return self.all_frame
end

function AETools._remap01(a,b,x)
    if x < a then return 0 end
    if x > b then return 1 end
    return (x-a)/(b-a)
end

function AETools._cubicBezier(p1, p2, p3, p4, t)
    return {
        p1[1]*(1.-t)*(1.-t)*(1.-t) + 3*p2[1]*(1.-t)*(1.-t)*t + 3*p3[1]*(1.-t)*t*t + p4[1]*t*t*t,
        p1[2]*(1.-t)*(1.-t)*(1.-t) + 3*p2[2]*(1.-t)*(1.-t)*t + 3*p3[2]*(1.-t)*t*t + p4[2]*t*t*t,
    }
end

function AETools._cubicBezier3D(p1, p2, p3, p4, t)
    if #p1 >= 3 then
        return {
            p1[1]*(1.-t)*(1.-t)*(1.-t) + 3*p2[1]*(1.-t)*(1.-t)*t + 3*p3[1]*(1.-t)*t*t + p4[1]*t*t*t,
            p1[2]*(1.-t)*(1.-t)*(1.-t) + 3*p2[2]*(1.-t)*(1.-t)*t + 3*p3[2]*(1.-t)*t*t + p4[2]*t*t*t,
            p1[3]*(1.-t)*(1.-t)*(1.-t) + 3*p2[3]*(1.-t)*(1.-t)*t + 3*p3[3]*(1.-t)*t*t + p4[3]*t*t*t,
        }
    else
        return {
            p1[1]*(1.-t)*(1.-t)*(1.-t) + 3*p2[1]*(1.-t)*(1.-t)*t + 3*p3[1]*(1.-t)*t*t + p4[1]*t*t*t,
            p1[2]*(1.-t)*(1.-t)*(1.-t) + 3*p2[2]*(1.-t)*(1.-t)*t + 3*p3[2]*(1.-t)*t*t + p4[2]*t*t*t,
            0,
        }
    end
end

function AETools:_cubicBezierSpatial(lenInfo, p1, p2, p3, p4, t)
    local p = 0
    if t <= 0 then
        p = 0
    elseif t >= 1 then
        p = 1
    else
        local ts = 0
        local te = 200
        for i=1,200,1 do
            if lenInfo[i] >= t then
                te = i
                ts = i-1
                break
            end
        end
        p = ts/200. + 0.005*(t-lenInfo[ts])/(lenInfo[te]-lenInfo[ts]+0.000001)
    end
    return self._cubicBezier3D(p1, p2, p3, p4, p)
end

function AETools:_cubicBezier01(_bezier_val, p, y_len)
    local x = self:_getBezier01X(_bezier_val, p, y_len)
    return self._cubicBezier(
        {0,0},
        {_bezier_val[1], _bezier_val[2]},
        {_bezier_val[3], _bezier_val[4]},
        {1, y_len},
        x
    )[2]
end

function AETools:_getBezier01X(_bezier_val, x, y_len)
    local ts = 0
    local te = 1
    -- divide and conque
    local times = 1
    repeat
        local tm = (ts+te)*0.5
        local value = self._cubicBezier(
            {0,0},
            {_bezier_val[1], _bezier_val[2]},
            {_bezier_val[3], _bezier_val[4]},
            {1, y_len},
            tm)
        if(value[1]>x) then
            te = tm
        else
            ts = tm
        end
        times = times +1
    until(te-ts < 0.001 and times < 50)

    return (te+ts)*0.5
end

function AETools._mix(a, b, x, type)
    if type == 1 then
        return a * (1-x) + b * x
    else
        return a + x
    end
end

function AETools:GetVal(_name, _progress)
    local content = self.attrs[_name]
    if content == nil then
        return nil
    end

    local cur_frame = _progress * self.all_frame + self.min_frame

    for i = 1, #content do
        local info = content[i]
        local start_frame = info[2][1]
        local end_frame = info[2][2]
        if cur_frame >= start_frame and cur_frame < end_frame then
            local cur_progress = self._remap01(start_frame, end_frame, cur_frame)
            local bezier = info[1]
            local value_range = info[3]
            local y_len = 1
            if (value_range[2][1] == value_range[1][1] and info[5] and info[5][1]==0 and #(value_range[1])==1) then
                y_len = 0
            end

            if #bezier > 4 then
                -- currently scale attrs contains more than 4 bezier values
                local res = {}
                for k = 1, 3 do
                    local cur_bezier = {bezier[k], bezier[k+3], bezier[k+3*2], bezier[k+3*3]}
                    local p = self:_cubicBezier01(cur_bezier, cur_progress, y_len)
                    res[k] = self._mix(value_range[1][k], value_range[2][k], p, y_len)
                end
                return res

            else
                local p = self:_cubicBezier01(bezier, cur_progress, y_len)
                if info[4] ~= nil and info[5] ~= nil and (info[4][1] == 6413 or info[4][1] == 6415) and info[5] and info[5][1] == 0 then
                    local coord = self:_cubicBezierSpatial(info['lenInfo'],
                                                            value_range[1], 
                                                            value_range[3], 
                                                            value_range[4], 
                                                            value_range[2], 
                                                            p)
                    return coord
                end

                if type(value_range[1]) == "table" then
                    local res = {}
                    for j = 1, #value_range[1] do
                        res[j] = self._mix(value_range[1][j], value_range[2][j], p, y_len)
                    end
                    return res
                end
                return self._mix(value_range[1], value_range[2], p, y_len)
            end
        end
    end

    local first_info = content[1]
    local start_frame = first_info[2][1]
    if cur_frame<start_frame then
        return deepcopy(first_info[3][1])
    end

    local last_info = content[#content]
    local end_frame = last_info[2][2]
    if cur_frame>=end_frame then
        return deepcopy(last_info[3][2])
    end

    return nil
end






---------- info_sticker/Helper.lua ----------

local Helper = {}


function Helper.getStyle0 (comp)
    if not comp then
        return
    end
    if comp.forceFlushCommandQueue then
        comp:forceFlushCommandQueue()
    end
    local letters = comp.letters
    if letters:size() > 0 then
        local letter0 = letters:get(0)
        return letter0.letterStyle
    end
end
function Helper.setFontSize (comp, size)
    local letters = comp.letters
    for i = 0, letters:size() - 1 do
        local letter = letters:get(i)
        letter.letterStyle.fontSize = size
    end
    if comp.forceFlushCommandQueue then
        comp:forceFlushCommandQueue()
    end
end

function Helper.disableText (node, transparentMaterial)
    local materials = Amaz.Vector()
    materials:pushBack(transparentMaterial)
    local Text = node:getComponent("Text")
    Text.canvas.renderToRT = true
    local Renderer = node:getComponent("MeshRenderer")
    Renderer.materials = materials
end
function Helper.enableText (node)
    local Text = node:getComponent("Text")
    Text.canvas.renderToRT = false
end

function Helper.attachCopy (node, name)
    local copy = node:searchEntity(name)
    if copy then
        node.scene:removeEntity(copy)
    end
    copy = node.scene:createEntity(name)

    local Transform0 = node:getComponent("Transform")
    local Transform1 = copy:cloneComponentOf(Transform0)
    Transform1.parent = Transform0
    Transform0.children:pushBack(Transform1)

    local MeshRenderer0 = node:getComponent("MeshRenderer")
    local MeshRenderer1 = copy:cloneComponentOf(MeshRenderer0)

    local Text0 = node:getComponent("Text")
    local Text1 = copy:cloneComponentOf(Text0)
    Text1.bloomEnable = false

    return {
        Entity = copy,
        Transform = Transform1,
        Renderer = MeshRenderer1,
        Text = Text1,
    }
end
function Helper.detachCopy (node, name)
    local copy = node:searchEntity(name)
    if copy then
        node.scene:removeEntity(copy)
    end
end



function Helper.isBreakLine (lastRowID, char)
    if char.rowth ~= lastRowID then
        return true
    end
    return char.utf8 == "\n"
end
function Helper.isVisibleChar (char)
    local lb = string.byte(char.utf8)
    return lb > 32 -- space
end
function Helper.splitByChar (chars)
    local frags = {}
    for i = 0, chars:size() - 1 do
        local char = chars:get(i)
        if Helper.isVisibleChar(char) then
            table.insert(frags, { line = char.rowth, char })
        end
    end
    return frags
end
function Helper.splitByWord (chars)
    local frag = { line = 0 }
    local frags = {}
    for i = 0, chars:size() - 1 do
        local char = chars:get(i)
        if Helper.isVisibleChar(char) then
            table.insert(frag, char)
            frag.line = char.rowth
        elseif #frag > 0 then
            table.insert(frags, frag)
            frag = {}
        end
    end
    if #frag > 0 then
        table.insert(frags, frag)
    end
    return frags
end
function Helper.splitByLine (chars)
    local frag = {}
    local frags = {}
    local rowID = 0
    for i = 0, chars:size() - 1 do
        local char = chars:get(i)
        if Helper.isVisibleChar(char) then
            table.insert(frag, char)
        elseif Helper.isBreakLine(rowID, char) then
            if #frag > 0 then
                table.insert(frags, frag)
                frag = {}
            end
            rowID = rowID + 1
        end
    end
    if #frag > 0 then
        table.insert(frags, frag)
    end
    return frags
end
function Helper.splitByNone (chars)
    local frag = {}
    local frags = {}
    for i = 0, chars:size() - 1 do
        local char = chars:get(i)
        if Helper.isVisibleChar(char) then
            table.insert(frag, char)
        end
    end
    if #frag > 0 then
        table.insert(frags, frag)
    end
    return frags
end



function Helper.convertSubtitle0 (data)
    local src = data.words
    local dst = {}
    for _, word in ipairs(src) do
        local text = word.text
        local startFragIndex = #dst + 1
        local totalVisibleCharCount = 0
        local charCount = 0
        local charIndex = 1
        for i = 1, #text do
            local code = string.byte(text, i)
            if code <= 32 then
                if charCount > 0 then
                    table.insert(dst, {text = string.sub(text, charIndex, i - 1), visibleCharCount = charCount})
                    charCount = 0
                    charIndex = i
                end
            else
                charCount = charCount + 1
                totalVisibleCharCount = totalVisibleCharCount + 1
            end
        end
        table.insert(dst, {text = string.sub(text, charIndex, #text), visibleCharCount = charCount})

        local t0 = word.start_time
        local dt = word.end_time - t0
        for i = startFragIndex, #dst do
            local frag = dst[i]
            frag.start_time = t0
            frag.end_time = t0 + dt * (frag.visibleCharCount / totalVisibleCharCount)
            t0 = frag.end_time
        end
    end
    for i = #dst, 1, -1 do
        local frag = dst[i]
        local next = dst[i + 1]
        if next then
            if frag.visibleCharCount == 0 then
                frag.start_time = next.start_time
            end
            frag.end_time = next.start_time
        end
        if frag.visibleCharCount == 0 then
            frag.start_time = frag.end_time
        end
    end
    data.words = dst
    return data
end

function Helper.splitSubtitle0 (words, chars, letters)
    local frags = {}
    local frag = {}
    local wordI = 1
    local charN = 0
    for charI = 0, chars:size() - 1 do
        local char = chars:get(charI)
        local letter = letters:get(charI)
        local word = words[wordI]
        if not word then
            break
        end
        table.insert(frag, {char = char, letter = letter})
        charN = charN + #char.utf8code
        if charN >= #word.text then
            frag.word = word
            table.insert(frags, frag)
            frag = {}
            charN = 0
            wordI = wordI + 1
        end
    end
    return frags
end
function Helper.splitSubtitle1 (words, start, chars, letters)
    local frags = {}
    local frag = {}
    local wordI = 1
    local charN = start
    for charI = 0, chars:size() - 1 do
        local char = chars:get(charI)
        local letter = letters:get(charI)
        local word = words[wordI]
        if not word then
            break
        end
        table.insert(frag, {char = char, letter = letter})
        charN = charN + #char.utf8code
        if charN >= #word.text then
            frag.word = word
            table.insert(frags, frag)
            frag = {}
            start = charN
            charN = 0
            wordI = wordI + 1
        end
    end
    return frags, start
end



function Helper.createFramebuffer (w, h)
    local rb = Amaz.RenderTexture()
    rb.attachment = Amaz.RenderTextureAttachment.NONE
    rb.filterMag = Amaz.FilterMode.LINEAR
    rb.filterMin = Amaz.FilterMode.LINEAR
    rb.depth = 1
    rb.width = w or 720
    rb.height = h or 1280
    return rb
end
function Helper.createMesh (locations, primitive)
    if not locations then
        locations = {Amaz.VertexAttribType.POSITION, Amaz.VertexAttribType.TEXCOORD0}
    end
    local attribs = Amaz.Vector()
    for _, loc in ipairs(locations) do
        local descriptor = Amaz.VertexAttribDesc()
        descriptor.semantic = loc
        attribs:pushBack(descriptor)
    end

    local mesh = Amaz.Mesh()
    mesh.vertexAttribs = attribs

    local mesh0 = Amaz.SubMesh()
    mesh0.mesh = mesh
    mesh0.primitive = primitive or Amaz.Primitive.TRIANGLES
    mesh:addSubMesh(mesh0)

    return mesh
end
function Helper.createTexture (w, h)
    local tex = Amaz.Texture2D()
    tex.filterMin = Amaz.FilterMode.LINEAR
    tex.filterMag = Amaz.FilterMode.LINEAR
    if w and h then
        tex.width = w
        tex.height = h
    end
    return tex
end








---------- AE.lua ----------
local AE_Position = {
	["Position"]={
		{{0.376377, 0, 0, 1, }, {0, 24, }, {{1361.5, 600, 0, }, {1000, 600, 0, }, {1301.25, 600, 0, }, {1060.25, 600, 0, }, }, {6413, }, {0, }, },
		{{0.166667, 0.166667, 0.666667, 0.666667, }, {24, 76, }, {{1000, 600, 0, }, {1000, 600, 0, }, {1000, 600, 0, }, {1000, 600, 0, }, }, {6413, }, {0, }, },
		{{0.968843, 0, 0.574798, 1, }, {76, 105, }, {{1000, 600, 0, }, {1505.5, 600, 0, }, {1084.25, 600, 0, }, {1421.25, 600, 0, }, }, {6413, }, {0, }, },
	},
}
local AE_Scale = {
	["Scale"]={
		{{0.396459566,0.396459566,0.33333333, 3.5e-8,3.5e-8,0.33333333, 0.25,0.25,0.66666667, 1.000000045,1.000000045,0.66666667, }, {0, 7, }, {{0, 0, 100, }, {112, 112, 100, }, }, {6414, }, {0, }, },
		{{0.33333333,0.33333333,0.33333333, 0,0,0.33333333, 0.66666667,0.66666667,0.66666667, 1,1,0.66666667, }, {7, 14, }, {{112, 112, 100, }, {98, 98, 100, }, }, {6414, }, {0, }, },
		{{0.33333333,0.33333333,0.33333333, 0,0,0.33333333, 0.66666667,0.66666667,0.66666667, 1,1,0.66666667, }, {14, 23, }, {{98, 98, 100, }, {100, 100, 100, }, }, {6414, }, {0, }, },
		{{0.166666667,0.166666667,0.166666667, 0.166666667,0.166666667,0.166666667, 0.66666667,0.66666667,0.66666667, 0.66666667,0.66666667,0.66666667, }, {23, 76, }, {{100, 100, 100, }, {100, 100, 100, }, }, {6414, }, {0, }, },
		{{0.33333333,0.33333333,0.33333333, 0,0,0.33333333, 0.66666667,0.66666667,0.66666667, 1,1,0.66666667, }, {76, 88, }, {{100, 100, 100, }, {98, 98, 100, }, }, {6414, }, {0, }, },
		{{0.33333333,0.33333333,0.33333333, 0,0,0.33333333, 0.66666667,0.66666667,0.66666667, 1,1,0.66666667, }, {88, 95, }, {{98, 98, 100, }, {112, 112, 100, }, }, {6414, }, {0, }, },
		{{0.753568225,0.753568225,0.33333333, 9e-9,9e-9,0.33333333, 0.66666667,0.66666667,0.66666667, 1,1,0.66666667, }, {95, 102, }, {{112, 112, 100, }, {0, 0, 100, }, }, {6414, }, {0, }, },
	},
}

local AE = {
	position = AE_Position,
	scale = AE_Scale,
}





---------- TextMain.lua ----------


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






---------- TextEntry.lua ----------


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