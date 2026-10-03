# 盲测结果 — stress-inoculation-rehearsal

## should-trigger-01
- activated_skill: stress-inoculation-rehearsal
- reason: 用户因"怕止损被触发"而无法下手执行，且主动问"怎么训练自己"，正是对最恐惧场景做心理预演的诉求；与问止损规则数值（stop-loss-discipline）不同。
- if_triggered_action: 引导用户在开盘前闭眼深呼吸，在脑海中反复完整"放电影"预演止损被触发的全过程，直到无须停顿一次播完。

## should-trigger-02
- activated_skill: stress-inoculation-rehearsal
- reason: 直接命中技能触发器"害怕隔夜"——用户对隔夜持仓这一具体场景有恐惧并伴随心慌，需要提前预演脱敏，而非当下处理情绪或改止损规则。
- if_triggered_action: 让用户每晚固定时间闭眼预演"持有隔夜仓→夜间波动→次日开盘"的完整画面，反复播放直到不再心跳加速、能流畅播完。

## should-trigger-03
- activated_skill: stress-inoculation-rehearsal
- reason: 用户明确表达"提前演练最坏情形"的诉求，与技能核心"开市前预演暴跌最坏情境、像接种疫苗一样对真实压力脱敏"完全一致。
- if_triggered_action: 指导用户写下跌暴跌剧本（点位、亏损金额、可能的操作冲动），闭眼深呼吸反复预演全程直至无须停顿完整播完。

## should-not-trigger-01
- activated_skill: stop-loss-discipline
- reason: 用户问的是止损规则本身该设多少，属于三分法止损体系（价格/指标/时间）的规则构建问题，不是对止损场景的恐惧训练，故不激活 stress-inoculation-rehearsal。
- if_triggered_action: 讲解三分法止损（基于价格/市场指标/时间）的适用场景，帮用户结合自身交易风格选定一类，并写下具体止损数值。

## should-not-trigger-02
- activated_skill: NONE
- reason: 用户只是在询问书籍第三章的内容概要，是纯知识性问题，不涉及任何交易心理状态或行为场景，14 个技能均无适用场景。
- if_triggered_action: 直接回答第三章内容概括，不启动任何心理技能，仅做内容性回应。

## edge-01
- activated_skill: internal-observer-emotion-data
- reason: 用户关注的是"亏钱恐惧导致的身体反应是否正常"，属于是否该相信自身感觉、把情绪当数据观察的范畴；未提到具体交易场景的预演或执行障碍。
- if_triggered_action: 教用户激活内部观察员：手心出汗时先抽离并命名"这是恐惧"，再把恐惧当作反向数据解读，而非急于消除或压抑它。
