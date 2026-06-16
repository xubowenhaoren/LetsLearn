"""Prompt templates for quiz generation."""

SUMMARIZE_PROMPT = """你是一位资深教材分析专家。请阅读以下文档的全部内容，识别出其中包含的{N}个最重要的核心知识点。

要求：
1. 每个知识点应该是一个独立的概念、技术或方法论
2. 知识点之间不要有重叠
3. 用简洁的中文短语命名（如 "TCP三次握手"、"MySQL索引原理"、"HashMap底层结构"）
4. 只返回 JSON 数组，不要其他内容

格式: ["知识点1", "知识点2", "知识点3", ...]

文档内容:
{chunks_text}
"""

MISTAKE_SUMMARIZE_PROMPT = """你是一位资深教材分析专家。请阅读以下文档的全部内容，识别出其中包含的{N}个最重要的核心知识点。

⚠️ 用户之前做错的题目涉及以下知识点，请务必将它们包含在知识点列表中：{mistake_titles}

要求：
1. 每个知识点应该是一个独立的概念、技术或方法论
2. 知识点之间不要有重叠
3. 用简洁的中文短语命名（如 "TCP三次握手"、"MySQL索引原理"、"HashMap底层结构"）
4. 必须包含上面列出的错题知识点
5. 只返回 JSON 数组，不要其他内容

格式: ["知识点1", "知识点2", "知识点3", ...]

文档内容:
{chunks_text}
"""


SINGLE_CARD_PROMPT = """你是一位经验丰富的AI导师。请根据以下资料为知识点"{key_point}"生成 **1张** 学习卡片。

每张卡片必须包含 4 个字段: title, aiExplanation, question, options。

━━━ title ━━━
直接使用知识点名称: "{key_point}"

━━━ aiExplanation ━━━
一篇 350-500字 的教学短文，按以下结构组织：

- 概念定义：一句话说清这个知识点是什么
- 核心原理：8-10句话讲清楚底层机制和运作方式
- 关键细节：2-3个容易忽略但重要的技术细节
- 常见误区：1个典型错误理解 + 正确认识

用通俗中文写作，像老师在给学生一对一辅导。避免干巴巴的罗列，要有逻辑递进。

━━━ question ━━━
一道4选1选择题。
- **答案必须能从 aiExplanation 原文中直接找到**，读完精讲就能答
- 考察是否认真读了精讲，不考延伸推理或外部知识
- 要具体：问"XXX的核心原理是什么"，不要"以下正确的是"

━━━ options ━━━
4个选项，每个含 label(A/B/C/D), text, isCorrect(bool), feedback。
- **先随机选择 A/B/C/D 之一作为正确选项**，把正确内容填入该选项
- 干扰项要看起来合理但确实与 aiExplanation 内容矛盾
- feedback 解释为什么对/错，有教学价值

只返回1个JSON对象（不是数组），不要其他任何文字。

格式: {{"title": "{key_point}", "aiExplanation": "...", "question": "...", "options": [{{"label": "A", "text": "...", "isCorrect": false, "feedback": "..."}}, ...]}}

详细资料: {detailed_content}
"""

