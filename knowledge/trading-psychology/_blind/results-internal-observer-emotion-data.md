# 盲测结果 — internal-observer-emotion-data

## should-trigger-01
- activated_skill: internal-observer-emotion-data
- reason: 用户"一交易就情绪化"正是该技能的典型触发词（一交易就情绪化/too emotional）；技能主张抽离出内部观察员、把情绪当作反向数据，直接对症"被情绪带跑"而非对抗情绪。
- if_triggered_action: 第一步引导用户回忆最近一次情绪化交易的触发瞬间，示范以观察员口吻复述当时感受，把"愤怒/恐惧"标记为数据而非行动指令，先观察再决定。

## should-trigger-02
- activated_skill: internal-observer-emotion-data
- reason: "心跳加速想立刻平仓，该听它的吗"对应技能触发器"该信直觉吗/should I trust my gut"；生理信号正是情绪数据，技能教用户区分"观察情绪"与"听从情绪"。
- if_triggered_action: 第一步让用户暂停操作，记录心跳、呼吸与"想平仓"念头，把情绪命名为观察对象；再对照持仓计划判断该念头是市场信号还是反应性情绪。

## should-trigger-03
- activated_skill: internal-observer-emotion-data
- reason: "脑子里全是负面想法"是技能明确列出的触发器；技能提供内部观察员法，让负面想法成为被观察的对象而非决策来源，正是处理此场景的核心手段。
- if_triggered_action: 第一步引导用户把负面想法逐条写下来并贴上"这是想法"标签，练习从观察员视角描述而非认同它们，再评估每条想法背后的信息价值。

## should-not-trigger-01
- activated_skill: emotional-temperature-gate
- reason: "今天很亢奋，该不该开仓"是开仓前即时状态自检，命中 emotional-temperature-gate 的"太亢奋/should I trade today"；该技能明确不适用于此场景。
- if_triggered_action: 第一步让用户用"激发水平×效价"给当前情绪温度打分，若落在危险区间则按规则今日不开仓，并复盘打分依据与离场标准。

## should-not-trigger-02
- activated_skill: market-meta-communication
- reason: "这波突破是不是假突破"属于市场信号解读，命中 market-meta-communication 的"假突破"触发器；这是对市场的判断问题，与交易者情绪类技能无关。
- if_triggered_action: 第一步用元信息框架拆解该突破的节奏、量能、广度与效率，逐一对照趋势健康度判据，给出是否为假突破的倾向性结论。

## edge-01
- activated_skill: internal-observer-emotion-data
- reason: "越强迫自己冷静越亏"正是对抗情绪反被情绪反噬的现象；该技能主张不压制情绪而以观察员抽离、把情绪当数据，能解释此悖论并给出替代路径。
- if_triggered_action: 第一步向用户指出"强迫冷静=与情绪对抗会放大它"，示范以观察员口吻命名当前情绪，引导其体验"观察而非控制"后再回到交易决策。
