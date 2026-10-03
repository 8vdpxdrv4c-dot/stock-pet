# 盲测结果 — solution-focused-trading

## should-trigger-01
- activated_skill: solution-focused-trading
- reason: 用户用"怎么戒掉"明确指向行为改变而非问题归因；报复性交易是待消除的坏行为，适合用找例外时刻、放大成功模式的方式戒除，而非深挖成因。
- if_triggered_action: 引导用户回忆某次亏损后没有立刻报复性交易的时刻，逐项分析当时条件（心情、间隔、计划），并设计延长该例外的可执行步骤。

## should-trigger-02
- activated_skill: solution-focused-trading
- reason: 话语直指"有没有做对过的时候"并想"找到并放大"，正是找例外、放大有效模式的核心诉求，完全命中本技能的设计主旨。
- if_triggered_action: 请用户列出曾做对的具体交易或决策时刻，逐条分析当时的仓位、准备、情绪与执行条件，挑出最可复现的一条作为放大样本。

## should-trigger-03
- activated_skill: solution-focused-trading
- reason: "想改掉过度交易"命中改掉坏行为的目标，且明确"不想只知道毛病在哪"，拒绝问题归因，正符合聚焦例外而非探究成因的方法定位。
- if_triggered_action: 邀请用户回忆那些想过要过度交易却忍住没做的时刻，分析当时是什么阻止了他，并探讨如何复制那个阻止条件。

## should-not-trigger-01
- activated_skill: fearless-trading-inventory
- reason: 用户要的是"找出不一致的地方"，即系统对照交易历史定位前后矛盾，这属于复盘执行缺口，正是 fearless-trading-inventory 的职责，而非找特例。
- if_triggered_action: 引导用户逐笔梳理近期交易记录，按仓位、准备、执行、角度、清仓五个维度对照成功与失败交易，标记所有不一致之处。

## should-not-trigger-02
- activated_skill: emotional-temperature-gate
- reason: 用户问"今天该不该开仓"且状态烦躁，属于交易前的情绪状态自检，应激活情绪温度门做开仓前判断，而非寻找交易特例。
- if_triggered_action: 让用户测量当前情绪的激发水平与效价，判定状态是否适合交易，若烦躁程度超标则建议今日离场或只做观察不操作。

## edge-01
- activated_skill: solution-focused-trading
- reason: 用户虽交易稀少但仍点名要用"找特例"方法，技能应激活；只是例外样本稀少，需扩大搜索范围，不能用近期高频交易记录来局限。
- if_triggered_action: 将例外搜索窗口放宽至全部历史与生活场景，包括"有过交易冲动却忍住"的时刻，从中提取一个可参照的例外样本。
