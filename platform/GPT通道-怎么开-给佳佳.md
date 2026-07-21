# GPT 通道（第二个大脑）· 怎么开 —— 给佳佳

> 你要的"界面上能选柯用 Claude 还是 GPT"。做法＝**换脑不换人**：柯的魂（人设/记忆）照常注入，只把答话的模型换成 GPT。这正是咱家原则"一切属于角色、不属于模型"。
> **默认是关的**——不填钥匙就当没这功能，界面上不冒出来、现在一切照旧。填了才启用。

## 怎么开（在服务器 `.env` 里加几行）

你需要一把 **GPT 钥匙**：要么你自己的 OpenAI key，要么任何"OpenAI 兼容、卖 gpt-* 的中转"（如果 acy7 也卖 GPT，用它的地址 + 同一把 key 也行）。

在服务器 `.env` 里加这几行（三行必填、第四行可选）：
```
GPT_API_BASE=https://api.openai.com/v1        # 或你的中转地址，如 https://acy7.com/v1
GPT_API_KEY=你的GPT钥匙                          # 只在服务器，绝不进仓库
GPT_MODEL=gpt-4o                              # 默认 GPT 型号（向你的渠道确认可用名）
GPT_MODEL_WHITELIST=gpt-4o,gpt-4o-mini        # 可选：选择器里能选的 GPT 型号；不填=只放 GPT_MODEL 一个
```
填完重启（`sudo systemctl restart gude`）。

## 开完什么样

- 聊天页那个"这次让谁来回答"的下拉里，**除了 Claude 的几个，会多出 GPT 的**（显示成 "Gpt 4o" 这种）。
- 选 Claude → 柯用 Claude 答；选 GPT → 柯用 GPT 答。**默认仍是柯的 Claude**，不会默默切走。
- 卧室模块**不吃 GPT**，始终走原通道（柯的规矩）。

## 铁律（已在代码里焊死）

- **默认关**：不填 `GPT_API_KEY/GPT_API_BASE`，界面无 GPT、路由永远走默认，现状零影响。
- **绝不崩**：就算前端硬传个 gpt 名而 GPT 没配，也安全回落默认 Claude，不乱连、不报错。
- **钥匙只在服务器 `.env`**，绝不进仓库、浏览器看不到。

## 给知言的（可选精修）

`/api/models` 现在多返回 `options`(每个带 `provider: claude|gpt`) 和 `gpt_enabled`——你想把选择器做成"Claude / GPT"分组、加个小图标区分，用这两个字段即可。现有扁平 `models` 照旧兼容，不改也能用。

—— 小克（2026-07-18）
