local Utils = require("common/Utils")
local Helper = require("info_sticker/Helper")


local SubtitleMain = {}
SubtitleMain.__index = SubtitleMain
function SubtitleMain.new (env)
    local self = setmetatable({}, SubtitleMain)
    return self
end


local Test

local function logcat (name, data)
    ---#ifdef DEV
--//    local file = io.open("/Users/jorgen/EffectMacaron/scriptEffect/"..name..".json", "w")
--//    io.output(file)
--//    io.write(cjson.encode(data))
--//    io.close(file)
    ---#endif
end

function SubtitleMain:onCreate (env)
    ---#ifdef DEV
--//    env.subtitle = cjson.decode(Test)
--//    env.subtitle = Helper.convertSubtitle0(env.subtitle)
--//    env.rootText.str = env.subtitle.text
--//    env.duration = 3
--//    env.transparent = env.scene.assetMgr:SyncLoad("material/transparent.material")
    ---#else
    ---#endif

    env.converter = Helper.convertSubtitle0
    self.transparent = env.transparent:instantiate()
end

function SubtitleMain:onShow (env)
    self.pages = nil

    self.copy = Helper.attachCopy(env.rootNode.entity, "copy")
    self.copy.Text.typeSettingParam.wordWrapWidth = 999999999
    self.copy.Text.typeSettingParam.typeSettingAlign = Amaz.TextAlign.CENTER
    Helper.disableText(env.rootNode.entity, self.transparent)

    local style0 = Helper.getStyle0(env.rootText)
    if style0 then
        self.color0 = style0.letterColorRGBA
        if self.color0.r > 0.95 and self.color0.g > 0.95 and self.color0.b > 0.95 then
            self.color1 = Amaz.Color(1 * self.color0.a,1 * self.color0.a,0.01 * self.color0.a,1 * self.color0.a)
        else
            self.color1 = self.color0
        end
        self.pages = self:pagination(env.subtitle.words, 3, 9999, 1)
    end
end

function SubtitleMain:onHide (env)
    Helper.detachCopy(env.rootNode.entity, "copy")
    Helper.enableText(env.rootNode.entity)
end

function SubtitleMain:onUpdate (env, elapsed)
    local pages = self.pages
    if not pages then
        return
    end

    for i, page in ipairs(self.pages) do
        if page.start_time <= elapsed and elapsed < page.end_time then
            local line = page[1]
            self.copy.SDFText.str = line.text
            self.copy.SDFText:forceTypeSetting()

            local frags = Helper.splitSubtitle0(line, self.copy.SDFText.chars, self.copy.Text.letters)
            for _, frag in ipairs(frags) do
                local color
                if frag.word.start_time <= elapsed and elapsed < frag.word.end_time then
                    color = self.color1
                else
                    color = Amaz.Color(self.color0.a,self.color0.a,self.color0.a,self.color0.a)
                end

                for _, tuple in ipairs(frag) do
                    local style = tuple.letter.letterStyle
                    style.letterColorRGBA = color
                end
            end
            if self.copy.Text.forceFlushCommandQueue then
                self.copy.Text:forceFlushCommandQueue()
            end
            return
        end
    end

    self.copy.SDFText.str = ""
    self.copy.SDFText:forceTypeSetting()
    if self.copy.Text.forceFlushCommandQueue then
        self.copy.Text:forceFlushCommandQueue()
    end
end

function SubtitleMain:onDestroy (env)
end


function SubtitleMain:pagination (words, maxWords, maxChars, maxLines)
    local frags = {}
    local frag = {visibleCharCount = 0, text = ""}
    local wordCounter = 0
    for _, word in ipairs(words) do
        word.text = string.gsub(word.text, "\r\n", "")
        word.text = string.gsub(word.text, "\n", "")
        word.text = string.gsub(word.text, "\t", " ")
        local text = frag.text..word.text
        local charCount = self.computePayload(text)
        local wordCount = word.visibleCharCount > 0 and 1 or 0
        if wordCounter + wordCount > maxWords or charCount > maxChars then
            table.insert(frags, frag)
            frag[1].text = Utils.trim(frag[1].text, 1)
            frag[#frag].text = Utils.trim(frag[#frag].text, -1)
            frag.text = Utils.trim(frag.text)
            frag.start_time = frag[1].start_time
            frag.end_time = frag[#frag].end_time
            frag = {visibleCharCount = 0, text = ""}
            wordCounter = 0
        end
        table.insert(frag, word)
        frag.visibleCharCount = frag.visibleCharCount + word.visibleCharCount
        frag.text = frag.text..word.text
        wordCounter = wordCounter + wordCount
    end
    if frag.visibleCharCount > 0 then
        table.insert(frags, frag)
        frag[1].text = Utils.trim(frag[1].text, 1)
        frag[#frag].text = Utils.trim(frag[#frag].text, -1)
        frag.text = Utils.trim(frag.text)
        frag.start_time = frag[1].start_time
        frag.end_time = frag[#frag].end_time
    end

    logcat("frags", frags)
    local pages = {}
    local page = {}
    for _, item in ipairs(frags) do
        table.insert(page, item)
        if #page >= maxLines then
            table.insert(pages, page)
            local page_text = {}
            for i = 1, #page - 1 do
                table.insert(page[i], {
                    visibleCharCount = 0,
                    start_time = page[i].end_time,
                    end_time = page[i].end_time,
                    text = "\n",
                })
                page[i].text = page[i].text.."\n"
                table.insert(page_text, page[i].text)
            end
            table.insert(page_text, page[#page].text)
            page.text = table.concat(page_text)
            page.start_time = page[1].start_time
            page.end_time = page[#page].end_time
            page = {}
        end
    end
    if #page > 0 then
        table.insert(pages, page)
        local page_text = {}
        for i = 1, #page - 1 do
            table.insert(page[i], {
                visibleCharCount = 0,
                start_time = page[i].end_time,
                end_time = page[i].end_time,
                text = "\n",
            })
            page[i].text = page[i].text.."\n"
            table.insert(page_text, page[i].text)
        end
        table.insert(page_text, page[#page].text)
        page.text = table.concat(page_text)
        page.start_time = page[1].start_time
        page.end_time = page[#page].end_time
    end
    logcat("pages", pages)
    return pages
end

function SubtitleMain.computePayload (str)
    local count = 0
    Utils.utf8_for(Utils.trim(str), function (index, bytes, code)
        if code >= 32 then
            count = count + 1
        end
    end)
    return count
end


---#ifdef DEV
--//Test = [[
--//{"words":[{"end_time":20,"start_time":0,"text":"and"},{"end_time":20,"start_time":20,"text":" "},{"end_time":100,"start_time":20,"text":"I"},{"end_time":100,"start_time":100,"text":" "},{"end_time":260,"start_time":100,"text":"grew"},{"end_time":260,"start_time":260,"text":" "},{"end_time":420,"start_time":260,"text":"up"},{"end_time":420,"start_time":420,"text":" "},{"end_time":500,"start_time":420,"text":"in"},{"end_time":500,"start_time":500,"text":" "},{"end_time":780,"start_time":540,"text":"New York"},{"end_time":780,"start_time":780,"text":" "},{"end_time":900,"start_time":820,"text":"and"},{"end_time":900,"start_time":900,"text":" "},{"end_time":1660,"start_time":900,"text":"Philadelphia"}]}
--//]]
---#endif

return SubtitleMain