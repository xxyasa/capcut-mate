




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
    for _, v in ipairs(src) do
        table.insert(dst, v)
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
    until _t - t_ < 0.00001

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
    B = B or R[3]
    G = G or R[2]
    R = B and R or R[1]
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

    return {H, S, L}
end
function Utils.hsl2rgb (H, S, L)
    L = L or H[3]
    S = S or H[2]
    H = L and H or H[1]
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
    return {R, G, B}
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
        local bytes = Utils.ucs4_size(string.byte(str, i))
        if bytes > 0 then
            if cb(str, i, bytes) then
                return
            end
            i = i + bytes
        else
            i = i + 1
        end
    end
end








---------- common/AEAdapter.lua ----------


---@class AEAdapter
local AEAdapter = {}
AEAdapter.__index = AEAdapter


function AEAdapter:new ()
    local self = setmetatable({}, AEAdapter)
    self._tracks = {}
    return self
end


---@param layerName string
---@param layerData table<string, table>
function AEAdapter:addKeyframes (layerName, layerData)
    for trackName, trackData in pairs(layerData) do
        local trackPath = layerName.."/"..trackName
        trackData.from_ae = true
        self._tracks[trackPath] = trackData
    end
end


---@param layerName string
---@param layerData table
function AEAdapter:addFrames (layerName, layerData)
    local fps = layerData.frameRate
    layerData = layerData.layer0
    for attrName, attrData in pairs(layerData) do
        if type(attrData) == "table" then
            local trackPath = layerName.."."..attrName
            attrData.fps = fps
            self._tracks[trackPath] = attrData
        end
    end
end


---@param layerName string
---@param layerData table
function AEAdapter:addAnimations (layerName, layerData)
    for attrName, attrData in pairs(layerData) do
        local trackPath = layerName..":"..attrName
        self._tracks[trackPath] = attrData
    end
end


---@param path string
---@param time number
---@return number|number[]
function AEAdapter:get (path, time)
    local track = self._tracks[path]
    if not track then
        return
    end

    if track.fps then
        return self:_solveFrame(track, time * track.fps)
    elseif track.from_ae then
        return self:_solveKeyframe(track, time)
    else
        return self:_solveAnimation(track, time)
    end
end


function AEAdapter:_solveFrame (track, frame)
    if #track > 0 then
        return self._interpolateFrame(track, frame)
    else
        local x = self._interpolateFrame(track.x, frame)
        local y = self._interpolateFrame(track.y, frame)
        return {x, y}
    end
end
function AEAdapter._interpolateFrame (array, frame)
    local n = #array - 1
    if frame <= 0 then
        return array[1]
    elseif frame >= n then
        return array[#array]
    end

    local i = math.floor(frame)
    local t = frame - i
    local k0 = array[i + 1]
    local k1 = array[i + 2]
    if type(k0) == "table" then
        local x = k0.x + (k1.x - k0.x) * t
        local y = k0.y + (k1.y - k0.y) * t
        return {x, y}
    else
        return k0 + (k1 - k0) * t
    end
end


function AEAdapter:_solveKeyframe (track, time)
    local K = track.k
    local N = #K
    if time <= K[1][1] then
        return Utils.table_slice(K[1], 2)
    elseif time >= K[N][1] then
        return Utils.table_slice(K[N], 2)
    end

    local interpolator = track.spatial and self._interpolateVector or self._interpolateScalar
    for i = 2, N do
        if time < K[i][1] then
            return interpolator(K[i - 1], K[i], track.s[i - 1], time)
        end
    end
    return Utils.table_slice(K[N], 2)
end
function AEAdapter._interpolateScalar (K0, K1, S, T)
    if S.hold then
        return Utils.table_slice(K0, 2)
    end
    local O = S.o
    local I = S.i
    local y = {}
    for i = 1, #K0 - 1 do
        local x1 = K0[1]
        local x2 = O[i][1]
        local x3 = I[i][1]
        local x4 = K1[1]
        local y1 = K0[i + 1]
        local y2 = O[i][2]
        local y3 = I[i][2]
        local y4 = K1[i + 1]
        y[i] = Utils.bezier4x2y(x1, x2, x3, x4, y1, y2, y3, y4, T)
    end
    return y
end
function AEAdapter._interpolateVector (K0, K1, S, T)
    if S.hold then
        return Utils.table_slice(K0, 2)
    end
    local O = S.o
    local I = S.i
    local P = S.p
    local L = P[1]

    local x1 = K0[1]
    local x2 = O[1]
    local x3 = I[1]
    local x4 = K1[1]
    local y1 = 0
    local y2 = O[2]
    local y3 = I[2]
    local y4 = L[#L]
    local l = Utils.bezier4x2y(x1, x2, x3, x4, y1, y2, y3, y4, T)

    local si = 1
    local ei = #L - 1
    local i
    while true do
        i = math.floor((si + ei) * 0.5 + 0.5)
        if l < L[i] then
            ei = i - 1
        elseif l > L[i + 1] then
            si = i + 1
        else
            break
        end
    end

    local t = Utils.step(L[i], L[i + 1], l)
    local v = {}
    for j = 2, #K0 do
        local v0 = P[j][i]
        local v1 = P[j][i + 1]
        v[j - 1] = v0 + (v1 - v0) * t
    end
    return v
end


function AEAdapter:_solveAnimation (track, time)
    local N = #track
    if time <= track[1][1] then
        return track[1][3]
    elseif time >= track[N][2] then
        return track[N][4]
    end

    for i = 1, N do
        local frag = track[i]
        if time <= frag[2] then
            local x = Utils.step(frag[1], frag[2], time)
            local m = frag[5]
            local y = type(m) == "function" and m(x) or Utils.bezier4x2y(0, m[1], m[3], 1, 0, m[2], m[4], 1, x)
            local v0 = frag[3]
            local v1 = frag[4]
            local v = {}
            for j = 1, #v0 do
                v[j] = Utils.mix(v0[j], v1[j], y)
            end
            return v
        end
    end
    return track[N][4]
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

function Helper.getFontSize (compNew, compOld, defaultValue)
    if compNew then
        if compNew.forceFlushCommandQueue then
            compNew:forceFlushCommandQueue()
        end
        local letters = compNew.letters
        if letters:size() > 0 then
            local letter0 = letters:get(0)
            local style = letter0.letterStyle
            if style then
                return style.fontSize
            end
        end
    end
    if compOld then
        return compOld.fontSize
    end
    return defaultValue or 24
end

function Helper.getTextColor (text)
    if not text then
        return
    end
    if text.forceFlushCommandQueue then
        text:forceFlushCommandQueue()
    end
    local letters = text.letters
    if letters:size() <= 0 then
        return
    end
    local letter0 = letters:get(0)
    local style0 = letter0.letterStyle
    if not style0 then
        return
    end
    local rgb = style0.letterColor
    local a = style0.letterAlpha
    style0.letterColor = Amaz.Vector3f(1, 1, 1)
    style0.letterAlpha = 1
    if text.forceFlushCommandQueue then
        text:forceFlushCommandQueue()
    end
    return Amaz.Vector4f(rgb.x, rgb.y, rgb.z, a), style0
end



function Helper.isBreakLine (lastRowID, char)
    if char.rowth ~= lastRowID then
        return true
    end
    return char.utf8code == "\n"
end
function Helper.isVisibleChar (char)
    local lb = string.byte(char.utf8code)
    return lb > 32 -- space
end
function Helper.splitByChar (chars)
    local frags = {}
    for i = 0, chars:size() - 1 do
        local char = chars:get(i)
        if Helper.isVisibleChar(char) then
            table.insert(frags, { char })
        end
    end
    return frags
end
function Helper.splitByWord (chars)
    local frag = {}
    local frags = {}
    for i = 0, chars:size() - 1 do
        local char = chars:get(i)
        if Helper.isVisibleChar(char) then
            table.insert(frag, char)
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
local AE = {
    ["ADBE Scale"] = {
        ["d"] = 3,
        ["k"] = {
            {0, 35, 35, 100},
            {0.26666666666667, 130, 130, 100},
            {0.6, 95, 95, 100},
            {1.1, 100, 100, 100}
        },
        ["s"] = {
            {["o"] = {{0.04444444444533, 50.83333333365}, {0.04444444444533, 50.83333333365}, {0.04444444444533, 100.283616950289}}, ["i"] = {{0.09333333333333, 130}, {0.09333333333333, 130}, {0.09333333333333, 100}}},
            {["o"] = {{0.32222222222333, 130}, {0.32222222222333, 130}, {0.32222222222333, 100}}, ["i"] = {{0.54444444444333, 95}, {0.54444444444333, 95}, {0.54444444444333, 100}}},
            {["o"] = {{0.683333333335, 95}, {0.683333333335, 95}, {0.683333333335, 100}}, ["i"] = {{1.016666666665, 100}, {1.016666666665, 100}, {1.016666666665, 100}}}
        }
    },
    ["ADBE Rotate Z"] = {
        ["d"] = 1,
        ["k"] = {
            {0, 46},
            {0.26666666666667, -25},
            {0.6, 5},
            {1.1, 0}
        },
        ["s"] = {
            {["o"] = {{0.04444444444533, 34.16666666643}}, ["i"] = {{0.09333333333333, -25}}},
            {["o"] = {{0.32222222222333, -25}}, ["i"] = {{0.54444444444333, 5}}},
            {["o"] = {{0.683333333335, 5}}, ["i"] = {{1.016666666665, 0}}}
        }
    },
    ["ADBE Opacity"] = {
        ["d"] = 1,
        ["k"] = {
            {0, 15},
            {0.16666666666667, 100}
        },
        ["s"] = {
            {["o"] = {{0.02777777777833, 29.16666666695}}, ["i"] = {{0.13888888888833, 85.83333333305}}}
        }
    }
}







---------- TextMain.lua ----------

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






---------- info_sticker/Patch0.lua ----------

--- Detect user configuration changes
local Patch0 = {}
Patch0.__index = Patch0


function Patch0.new (env, compNew, compOld)
    local self = setmetatable({}, Patch0)
    self.compNew = compNew
    self.compOld = compOld
    self.compOld:forceTypeSetting()
    self:_cacheInitialPosition()
    return self
end


function Patch0:isDirty (env)
    self.compOld:forceTypeSetting()
    if self:_checkInitialPosition() then
        self:_cacheInitialPosition()
        return true
    end
    return false
end

function Patch0:_cacheInitialPosition ()
    self._initialPosition = {}
    local cache = {}
    local chars = self.compOld.chars
    for i = 0, chars:size() - 1 do
        local char = chars:get(i)
        table.insert(cache, char.initialPosition:copy())
    end
    self.cache = cache
end

function Patch0:_checkInitialPosition ()
    local cache = self.cache
    local chars = self.compOld.chars
    if chars:size() ~= #cache then
        return true
    end
    for i = 0, chars:size() - 1 do
        local char = chars:get(i)
        local p0 = char.initialPosition
        local p1 = cache[i + 1]
        if p0.x ~= p1.x or p0.y ~= p1.y or p0.z ~= p1.z then
            return true
        end
    end
    return false
end







---------- TextEntry.lua ----------


local TextAnim = {}
TextAnim.__index = TextAnim


function TextAnim.new ()
    local self = setmetatable({}, TextAnim)
    self.curTime = 0.0
    self.duration = 5.0
    self.w = 0
    self.h = 0
    self._visible = false
    self._dirty = false
    self._main = TextMain.new()
    return self
end

function TextAnim:onStart (comp)
    self.scene = comp.entity.scene
    local cameraEntity = self.scene:findEntityBy("InfoSticker_camera_entity")
    if cameraEntity then
        self.camera = cameraEntity:getComponent("Camera")
    end
    self.rootPath = debug.getinfo(1, "S").source:match("@?(.*/)")
    self.rootNode = comp.entity:getComponent("Transform")
    self.rootText = comp.entity:getComponent("Text")
    self.rootTextOld = comp.entity:getComponent("SDFText")
    if not self.rootTextOld then
        if self.rootText then
            self.rootTextOld = comp.entity:addComponent("SDFText")
            self.rootTextOld:setTextWrapper(self.rootText)
        end
    end
    self._main:onCreate(self)
    self.patch0 = Patch0.new(self, self.rootText, self.rootTextOld)
end

function TextAnim:onEnter ()
    if not self.visible then
        self._main:onShow(self)
        self._visible = true
    end
    self._dirty = true
end

function TextAnim:onLeave ()
    if self._visible then
        self._main:onHide(self)
        self._visible = false
    end
end

function TextAnim:clear ()
    self:onLeave()
end

function TextAnim:setDuration (duration)
    self.duration = duration
end

function TextAnim:seek (time)
    if not self._visible then
        return
    end
    local w = Amaz.BuiltinObject:getOutputTextureWidth()
    local h = Amaz.BuiltinObject:getOutputTextureHeight()
    if self.w ~= w or self.h ~= h then
        self.w = w
        self.h = h
        self._dirty = true
    end
    if self.patch0:isDirty(self) then
        self._dirty = true
    end
    if self._dirty then
        self._main:onChange(self)
        self._dirty = false
    end
    self._main:onUpdate(self, time)
end


---#ifdef DEV
--//function TextAnim:onUpdate (comp, dt)
--//    self:seek(self.seekTime or math.min(self.curTime, self.duration))
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