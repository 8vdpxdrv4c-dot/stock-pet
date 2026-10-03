# 盲测评审结果 — stop-loss-discipline（6 条 prompt）

### should-trigger-01

用户说: 我怎么设止损才不会老被扫掉？

- activated_skill: stop-loss-discipline
- reason: 问的是止损规则本身如何设计（避免被扫掉），属于三分法止损体系（价格/市场指标/时间）的规则设定问题，是该技能的核心适用场景，而非执行或心态问题。
- if_triggered_action: 先讲解三分法止损（价格、市场指标、时间三类）各自的适用场景与优缺点，再引导其按交易周期选择并预先写死规则。

### should-trigger-02

用户说: 我又死扛了，把短线扛成了中线。

- activated_skill: stop-loss-discipline
- reason: 用户死扛且把短线做成中线，是该技能描述中原文列举的典型触发（舍不得砍/死扛/把短线做成中线），属止损执行失败的核心场景，无需怀疑其他技能。
- if_triggered_action: 帮其把止损预设为无条件执行的条件（含时间止损），并重新定义止损为假设证伪而非亏损，立即写定硬性止损计划。

### should-trigger-03

用户说: 止损好痛，每次割肉都像承认自己失败了。

- activated_skill: stop-loss-discipline
- reason: 把割肉等同于个人失败，正是该技能要重构的"失败内化"信念；其核心即把止损定义为假设证伪、把失败当作做生意的成本不内化，直接对症。
- if_triggered_action: 引导认知重构：止损触发等于交易假设被证伪而非人格失败，并把止损视为做生意的正常成本，配合写死规则降低决策情绪。

### should-not-trigger-01

用户说: 我知道止损规则，但就是不敢执行，怎么训练？

- activated_skill: stress-inoculation-rehearsal
- reason: 用户已知止损规则，缺的是执行时的勇气与训练方法；"不敢执行"属恐惧，正对该技能"因恐惧执行不了计划"及开市前预演最坏情形脱敏的训练场景，非规则问题。
- if_triggered_action: 引导其在开市前闭眼深呼吸、脑中反复预演"止损被触发"的最坏画面，直到能完整播完不再停顿，形成对真实压力的脱敏。

### should-not-trigger-02

用户说: 我现在这个仓位今天该不该平掉？

- activated_skill: NONE
- reason: 用户问的是某个具体仓位的即时处置（今天该不该平），属"具体买卖点/止损数值"类咨询，被多个技能明示排除；14 个技能均面向规则、状态或复盘，不处理单笔即时操作建议。
- if_triggered_action: 不激活任何技能；可提示其按已定的交易计划与止损规则执行，或先检查当下情绪状态是否适合做决策。

### edge-01

用户说: 时间止损是不是只适合日内交易？

- activated_skill: stop-loss-discipline
- reason: 时间止损是该技能三分法体系中的一类（且作者最喜欢），用户问其适用范围属于止损规则本身的认知探讨，正好落在"想知道三分法止损体系"的用途内。
- if_triggered_action: 解释时间止损的原理（按持仓时间证伪假设）及其对日内与波段交易的适用差异，厘清时间止损的适用范围边界。
