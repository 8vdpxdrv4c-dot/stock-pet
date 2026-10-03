# 盲测结果 — market-meta-communication

## should-trigger-01

- activated_skill: market-meta-communication
- reason: 指数创新高（信息）与只有少数股票创新高（广度不足=元信息）的错位，正是"怎么走比走到哪更重要"框架的核心场景，直接命中"指数涨个股不涨/广度"触发词，需用元信息判断趋势健康度。
- if_triggered_action: 先区分"信息"与"元信息"：让用户列出指数涨幅、创新高个股数量与量能数据，判断广度与效率是否支撑新高，而非只看点位。

## should-trigger-02

- activated_skill: market-meta-communication
- reason: 突破真假不取决于价格本身，而取决于突破时的量能、广度、节奏是否配合，这正是元信息解读框架处理的问题，直接命中"假突破"触发词。
- if_triggered_action: 把"真假"转成可检验清单：突破当天量能是否放大、参与创新高的个股广度、是否反复试探后放量确认，逐项对照判断。

## should-trigger-03

- activated_skill: market-meta-communication
- reason: 趋势健康度正是该技能的核心问题——健康与否藏在节奏、量能、广度、效率等元信息里，直接命中"趋势健不健康"触发词，属于"怎么走"的解读。
- if_triggered_action: 先教"信息 vs 元信息"框架，再让用户列出常用健康度指标（量能/广度/效率/节奏），并讲解效率下降、期望落空、广度不足三大破坏信号。

## should-not-trigger-01

- activated_skill: contrarian-pinball-edge
- reason: 用户核心诉求是"感觉要见顶、要不要反着做"，属于逆向交易决策而非市场元信息解读；该技能恰好警示"没有统计验证就盲目反着做"是陷阱，命中"逆向交易/反着来"。
- if_triggered_action: 先质疑"感觉"：要求用户提供见顶的统计证据（创新低个股占比、恐慌数据），在验证前不采取反向操作，避免用情绪代替数据。

## should-not-trigger-02

- activated_skill: NONE
- reason: 这是纯技术指标的计算请求，属于数值运算而非交易心理、市场解读或行为干预，14 个技能均为心理/行为技能，无一涵盖指标计算场景。
- if_triggered_action: 无需激活任何技能，直接给出 20 日均线的计算公式与结果（近 20 个交易日收盘价的算术平均），不引入心理框架。

## edge-01

- activated_skill: market-meta-communication
- reason: "背离"直接命中触发词，用户不确定信号是否有效，本质是要用元信息（量能、广度、效率）交叉验证背离的可信度，而非孤立看单一指标，属于该技能框架。
- if_triggered_action: 引导用元信息交叉验证：背离出现时量能是否配合、上涨/下跌广度是否同步、信号是否在合理时间窗口内获得价格确认，再定有效性。
