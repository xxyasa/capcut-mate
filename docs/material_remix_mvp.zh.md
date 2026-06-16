# 素材混剪 MVP 方案

## 目标

基于当前 CapCut Mate 的草稿生成能力，提供一个面向“素材批量混剪”的 MVP：

- 用户提供 N 个视频素材，支持本地文件和 `http/https` 远程素材。
- 用户输入需要生成的混剪数量。
- 系统随机抽取、裁切、排序这些视频素材，生成多个剪映草稿。
- 每个素材片段之间自动添加合适的转场动画。
- 自动选择一条合适的 BGM 并铺到整条视频。
- 后续可扩展为自动生成字幕和口播。

MVP 的核心产物是“剪映草稿”，用户可以通过现有 Electron 客户端下载/写入剪映草稿目录，也可以继续调用 `gen_video` 做云端导出。

## 当前项目可复用能力

当前项目已经具备以下能力：

| 能力 | 已有接口/模块 | 说明 |
| --- | --- | --- |
| 创建草稿 | `POST /openapi/capcut-mate/v1/create_draft` | 基于模板创建剪映草稿，返回 `draft_url` |
| 添加视频 | `POST /openapi/capcut-mate/v1/add_videos` | 支持批量视频、裁切、音量、转场、遮罩、位置缩放 |
| 添加音频 | `POST /openapi/capcut-mate/v1/add_audios` | 支持批量音频添加 |
| 添加字幕 | `POST /openapi/capcut-mate/v1/add_captions` | 支持字幕、关键词高亮、动画、花字 |
| 保存草稿 | `POST /openapi/capcut-mate/v1/save_draft` | 持久化草稿 |
| 下载草稿文件列表 | `GET /openapi/capcut-mate/v1/get_draft` | Electron 客户端用它把草稿写入剪映目录 |
| Electron 写入本地剪映 | `desktop-client/nodeapi/download.js` | 下载远程草稿文件并重写素材路径 |

重要限制：

当前 `add_videos` 和 `add_audios` 的 schema 会校验素材地址必须是 `http://` 或 `https://`。所以 MVP 如果输入是本地路径，不能直接把 `/Users/.../a.mp4` 或 `C:\...\a.mp4` 传给现有接口。

## MVP 技术决策

MVP 推荐采用“统一 URL 输入”的方式，尽量不改已有草稿编辑核心逻辑：

1. 如果用户输入的是 `http/https` 素材 URL，直接进入混剪编排。
2. 如果用户选择的是本地素材，Electron 或后端将本地素材复制到服务可访问目录，例如：

   ```text
   output/materials/{task_id}/videos/
   output/materials/{task_id}/bgm/
   ```

3. 本地素材通过 `DOWNLOAD_URL` 或本地静态服务生成 HTTP URL：

   ```text
   http://127.0.0.1/output/materials/{task_id}/videos/a.mp4
   ```

4. 后端混剪编排服务统一拿到 URL 列表，继续调用现有 `create_draft`、`add_videos`、`add_audios`、`save_draft`。
5. 生成的 `draft_url` 仍然走现有 Electron 下载草稿逻辑。

这样做的好处是：

- 复用当前接口，不破坏已有 `add_videos/add_audios` 校验。
- 远程部署和本地部署逻辑一致。
- 后续如果要优化性能，再新增 `local_video_path/local_audio_path` 模式，跳过“下载素材到草稿目录”的中间步骤。

## 新增 MVP 接口

建议新增一个编排接口：

```text
POST /openapi/capcut-mate/v1/material_remix
```

### 请求参数

```json
{
  "videos": [
    {
      "type": "url",
      "url": "https://example.com/video/a.mp4"
    },
    {
      "type": "local",
      "path": "/Users/xinyu/Videos/b.mp4"
    }
  ],
  "video_urls": [
    "http://127.0.0.1/output/materials/task_001/videos/a.mp4",
    "http://127.0.0.1/output/materials/task_001/videos/b.mp4",
    "http://127.0.0.1/output/materials/task_001/videos/c.mp4"
  ],
  "output_count": 5,
  "width": 1080,
  "height": 1920,
  "target_duration": 30000000,
  "clip_min_duration": 2000000,
  "clip_max_duration": 5000000,
  "bgms": [
    {
      "type": "url",
      "url": "https://example.com/bgm/upbeat.mp3"
    },
    {
      "type": "local",
      "path": "/Users/xinyu/Music/lifestyle.mp3"
    }
  ],
  "bgm_urls": [
    "http://127.0.0.1/output/materials/task_001/bgm/upbeat_01.mp3",
    "http://127.0.0.1/output/materials/task_001/bgm/lifestyle_01.mp3"
  ],
  "style": "auto",
  "mute_original": true,
  "seed": null,
  "caption": {
    "enabled": false,
    "items": []
  },
  "voiceover": {
    "enabled": false,
    "audio_url": ""
  }
}
```

### 字段说明

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `videos` | 否 | 原始素材输入，支持 `type=url` 和 `type=local` |
| `video_urls` | 否 | 已 URL 化的视频素材；MVP 可以先只实现这个字段 |
| `output_count` | 是 | 需要生成的混剪草稿数量 |
| `width` / `height` | 否 | 草稿画布尺寸，默认 `1080x1920`，适合短视频竖屏 |
| `target_duration` | 否 | 单条混剪目标时长，单位微秒，默认 30 秒 |
| `clip_min_duration` | 否 | 单个片段最短时长，默认 2 秒 |
| `clip_max_duration` | 否 | 单个片段最长时长，默认 5 秒 |
| `bgms` | 否 | 原始 BGM 输入，支持 `type=url` 和 `type=local` |
| `bgm_urls` | 否 | 已 URL 化的 BGM 池；MVP 可以先只实现这个字段，不传则使用内置 BGM 池 |
| `style` | 否 | 混剪风格，MVP 支持 `auto`、`fast`、`smooth` |
| `mute_original` | 否 | 是否静音原视频，默认 true |
| `seed` | 否 | 随机种子；传入后可复现同一组混剪结果 |
| `caption` | 否 | 字幕预留参数，MVP 可不启用 |
| `voiceover` | 否 | 口播预留参数，MVP 可不启用 |

### 响应参数

```json
{
  "drafts": [
    {
      "draft_url": "https://capcut-mate.jcaigc.cn/openapi/capcut-mate/v1/get_draft?draft_id=202605251200001234abcd",
      "duration": 30000000,
      "seed": 112233,
      "selected_videos": [
        "http://127.0.0.1/output/materials/task_001/videos/c.mp4",
        "http://127.0.0.1/output/materials/task_001/videos/a.mp4"
      ],
      "bgm_url": "http://127.0.0.1/output/materials/task_001/bgm/upbeat_01.mp3"
    }
  ]
}
```

## 混剪流程

每生成一条混剪草稿，执行以下步骤：

1. 标准化素材输入：`http/https` 直接保留，本地文件复制到 `output/materials/{task_id}` 后转为 URL。
2. 调用 `create_draft` 创建新草稿。
3. 读取所有视频素材时长。
4. 根据目标时长随机生成片段列表。
5. 为每个片段分配时间轴位置。
6. 为相邻片段选择转场。
7. 调用 `add_videos` 一次性添加所有视频片段。
8. 自动选择 BGM。
9. 调用 `add_audios` 添加 BGM。
10. 如果启用字幕，调用 `add_captions`。
11. 如果启用口播，优先添加口播音轨，再按口播时长对齐字幕。
12. 调用 `save_draft` 保存草稿。
13. 返回 `draft_url`。

## 随机混剪算法

MVP 的随机策略保持简单可控：

1. 对输入素材列表洗牌。
2. 每次从素材池中取一个视频，取完一轮后重新洗牌。
3. 为每个素材随机选择片段时长：

   ```text
   clip_duration = random(clip_min_duration, clip_max_duration)
   ```

4. 如果素材实际时长大于 `clip_duration`，随机选择素材内部起点：

   ```text
   source_start = random(0, video_duration - clip_duration)
   source_end = source_start + clip_duration
   ```

5. 时间轴上顺序拼接：

   ```text
   timeline_start = previous_timeline_end
   timeline_end = timeline_start + clip_duration
   ```

6. 累计到 `target_duration` 后停止；最后一个片段可裁短以贴合目标时长。

MVP 不做复杂的画面理解，只做基于随机种子、时长、转场和 BGM 的批量差异化生成。

## 转场选择策略

`add_videos` 已支持在 `video_infos` 中传入：

```json
{
  "transition": "淡入淡出",
  "transition_duration": 500000
}
```

MVP 建议内置一个安全转场池：

```text
淡入淡出
叠化
模糊
推近
拉远
左右滑动
上下滑动
闪白
```

按风格选择：

| 风格 | 转场策略 |
| --- | --- |
| `smooth` | 多用 `淡入淡出`、`叠化`、`模糊`，时长 500ms-900ms |
| `fast` | 多用 `闪白`、`推近`、`左右滑动`，时长 250ms-500ms |
| `auto` | 混合选择，默认 500ms |

兜底规则：

- 第一段不需要转场。
- 每段的 `transition_duration` 不应超过该片段时长的 25%。
- 如果某个转场名称在剪映元数据中不可用，回退到 `淡入淡出`。

## BGM 自动选择策略

MVP 不做音乐内容理解，使用规则选择：

1. 如果用户传入 `bgm_urls` 或 `bgms`，标准化后从用户提供的 BGM 列表中随机选择一首。
2. 如果没有传入，使用服务端内置 BGM 池。
3. 根据视频风格筛选：

   | 风格 | BGM 标签 |
   | --- | --- |
   | `fast` | upbeat、electronic、dance |
   | `smooth` | lifestyle、chill、warm |
   | `auto` | 随机 |

4. BGM 从 0 秒开始铺满整条视频。
5. 如果 BGM 比视频短，MVP 可以先只铺一遍；后续版本支持循环铺满。
6. 原视频声音默认静音，即 `video_infos[].volume = 0`；如果需要保留环境音，可设为 `0.1-0.3`。

调用 `add_audios` 时，生成类似：

```json
[
  {
    "audio_url": "http://127.0.0.1/output/materials/task_001/bgm/upbeat_01.mp3",
    "start": 0,
    "end": 30000000,
    "volume": 0.45
  }
]
```

## 字幕和口播预留

MVP 阶段先预留字段，不强制实现自动生成。

### 阶段 2：自动字幕

字幕来源可以有三种：

1. 用户直接传入字幕文案。
2. 根据口播文本自动切分字幕。
3. 对口播音频做 ASR，生成时间戳字幕。

最终调用现有 `add_captions`：

```json
[
  {
    "start": 0,
    "end": 2500000,
    "text": "今天分享一组高质感穿搭",
    "font_size": 12,
    "keyword": "高质感|穿搭",
    "keyword_color": "#ff7100",
    "in_animation": "渐显"
  }
]
```

### 阶段 2：自动口播

口播建议作为单独音轨添加：

1. 用户输入口播文案。
2. TTS 服务生成口播音频 URL。
3. 调用 `add_audios` 添加口播音轨。
4. BGM 音量降低到 `0.15-0.25`。
5. 字幕根据口播文本或 ASR 结果自动生成。

音频层级建议：

| 音轨 | 音量 |
| --- | --- |
| 原视频 | 0 或 0.1 |
| BGM | 无口播 0.35-0.55，有口播 0.15-0.25 |
| 口播 | 0.9-1.0 |

## 服务端模块设计

建议新增文件：

```text
src/schemas/material_remix.py
src/service/material_remix.py
```

并在：

```text
src/router/v1.py
src/service/__init__.py
```

中注册接口和服务。

### service 伪代码

```python
def material_remix(req: MaterialRemixRequest) -> MaterialRemixResponse:
    video_urls = normalize_material_inputs(req.videos, req.video_urls)
    bgm_urls = normalize_material_inputs(req.bgms, req.bgm_urls)

    results = []
    for index in range(req.output_count):
        seed = req.seed or gen_seed()
        randomizer = random.Random(seed + index)

        draft_url = create_draft(width=req.width, height=req.height)
        video_plan = build_random_video_plan(
            video_urls=video_urls,
            target_duration=req.target_duration,
            clip_min_duration=req.clip_min_duration,
            clip_max_duration=req.clip_max_duration,
            style=req.style,
            randomizer=randomizer,
        )

        add_videos(
            draft_url=draft_url,
            video_infos=json.dumps(video_plan.video_infos, ensure_ascii=False),
        )

        bgm_url = select_bgm(bgm_urls, req.style, randomizer)
        if bgm_url:
            add_audios(
                draft_url=draft_url,
                audio_infos=json.dumps([
                    {
                        "audio_url": bgm_url,
                        "start": 0,
                        "end": video_plan.duration,
                        "volume": 0.45,
                    }
                ], ensure_ascii=False),
            )

        if req.caption.enabled:
            add_captions(...)

        save_draft(draft_url)
        results.append(...)

    return MaterialRemixResponse(drafts=results)
```

## Electron 客户端 MVP 页面

建议新增一个“素材混剪”页面：

1. 选择本地视频素材，支持多选。
2. 输入生成数量。
3. 选择视频比例：竖屏 `1080x1920`、横屏 `1920x1080`、方形 `1080x1080`。
4. 选择风格：自动、快节奏、平滑。
5. 可选上传/选择 BGM 文件夹。
6. 点击“生成草稿”。
7. 展示生成进度和草稿下载地址。
8. 支持一键写入剪映草稿目录。

MVP 可以先不做复杂素材管理，直接把用户选择的本地文件复制到 `output/materials/{task_id}`，再交给后端混剪接口。

## 本地素材处理方案

### MVP 方案：统一 URL 输入

流程：

```text
http/https 素材 URL
  -> 直接调用 material_remix
  -> material_remix 调用 add_videos/add_audios
  -> 草稿下载到剪映目录

本地视频路径
  -> 复制到 output/materials/{task_id}/videos
  -> 生成 http(s) URL
  -> 调用 material_remix
  -> material_remix 调用 add_videos/add_audios
  -> 草稿下载到剪映目录
```

优点：

- 改动小。
- 与现有 `add_videos` 兼容。
- 适合本地部署和 Docker 部署。
- 同时支持远程 URL 素材和本地素材。

缺点：

- 本地素材会经历一次复制和一次下载到草稿目录，磁盘占用更高。
- 远程 URL 素材仍会被下载到草稿目录，确保剪映本地可访问。

### 后续优化：支持 local path

后续可以扩展 `add_videos`：

```json
{
  "video_url": "",
  "local_video_path": "/Users/xinyu/Videos/a.mp4"
}
```

当 `local_video_path` 存在时，直接复制到草稿 `assets/videos` 目录，跳过 HTTP 下载。

## MVP 验收标准

1. 输入 5 个视频素材，本地路径和 `http/https` URL 混用，生成数量为 3，最终得到 3 个不同的 `draft_url`。
2. 每个草稿都包含多个随机视频片段。
3. 每个片段之间有转场。
4. 每个草稿都有 BGM。
5. Electron 客户端可以把草稿写入剪映目录。
6. 剪映中能打开草稿并正常预览。
7. 同一个 `seed` 可以复现相同混剪结果。
8. 不传字幕/口播时流程正常；传预留字段时不影响主流程。

## 第一版实施清单

1. 新增 `material_remix` schema。
2. 新增 `material_remix` service。
3. 注册 `/material_remix` 路由。
4. 增加 BGM 配置文件，例如 `config/bgm.json`。
5. 增加转场候选池配置。
6. Electron 新增本地素材选择和复制到 `output/materials/{task_id}` 的能力。
7. Electron 调用 `/material_remix`，展示返回的 `draft_url`。
8. 复用现有下载草稿逻辑写入剪映目录。

## 风险和注意事项

- 当前 `add_videos/add_audios` 只接受 HTTP URL，本地路径需要先 URL 化。
- BGM 自动选择 MVP 只是规则随机，不保证音乐语义完全匹配画面。
- 不同剪映版本可用转场名称可能不同，需要做回退。
- 大量素材会占用 `output/materials` 和 `output/draft` 磁盘空间，需要后续补清理策略。
- 如果目标机器无法访问 `DOWNLOAD_URL`，Electron 下载草稿或素材会失败。
- 如果开启云端导出，需要确认剪映安装路径、API key、对象存储配置都已正确配置。
