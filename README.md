# 人间道周易解卦 Skill

Codex 技能名：`renjiandao-yijing`。校验三面六投起卦，并从随附的倪海厦《人间道》逐次完整回读前言、主变卦章节和原页，区分易辞原文、作者解释和针对问题的推断。

本仓库包含代码、规则、64 卦定位索引、使用说明和用户明确要求随技能上传的原书 PDF，**不包含私人占问记录或阅读包**。原书用于逐次回读核对，不为其声明新的开放许可证。来源读取不能以索引、旧答案或模型记忆代替。

## 安装

已在 Python 3.12 验证；源码要求 Python 3.10 或更高。先下载到独立目录：

```bash
git clone https://github.com/Yixiao-Zhang1214/liuyao-skill.git renjiandao-yijing
cd renjiandao-yijing
python3 -m pip install -r requirements.txt
```

将整个目录作为 `renjiandao-yijing` 放入 Codex 的技能目录（通常为 `~/.codex/skills/`，自定义 CODEX_HOME 时使用其 skills 目录）。若已有同名技能，先比较并备份，不直接覆盖。技能的操作说明见 [SKILL.md](SKILL.md)。

## 随附原书与来源校验

仓库随附用户提供的 [《人间道》PDF](references/book/人间道.pdf)，位置为：

```text
references/book/人间道.pdf
```

已确认的版本为 146 个 PDF 页，正文纸本 136 页；指纹为：

```text
dbddd248eea899dbc5914c17f149f2fc555cb4d327443d03896f099b61b28c10
```

核对来源：

```bash
python3 scripts/source_reader.py check-source
```

缺少原书或指纹不符时，原书解读停止，不自动联网下载或拿另一版本替代。仅起卦计算可在没有 PDF 时使用。同版指纹不等于文字全无错误：已知疑字保留在索引中，实际解读还须核对原页。不同版本需明确重新核对章节及疑字后采用新索引，不能只换哈希放行。

## 使用

在 Codex 中提出问题并附记录或卦图，例如：

```text
请用 $renjiandao-yijing 校验这个卦，先从《人间道》解读卦辞。
```

起卦约定：正反名称与阴阳属性分开；本项目默认正=阳、反=阴。三阳老阳、二阳少阳、一阳少阴、零阳老阴，六次从下向上记录。这是用户指定的多数面规则，不混用另一种硬币数值求和法。

```bash
python3 scripts/hexagram.py cast --tosses '三正、一正二反、两正一反、两反一正、两正一反、三正' --positive yang
python3 scripts/hexagram.py resolve --main '风火家人' --moving '3' --changed '风雷益'
```

动爻取辞采用项目约定的朱熹变占通行表；两动较高者为主，四动较低静爻为主，三动使用贞悔并看的简化版本，不冒称完整严格法。规则与倪海厦书中解释分别标明。详见 [起卦规则](references/casting-rules.md) 和 [原书阅读协议](references/reading-protocol.md)。

每次解读新建阅读包，重新从 PDF 抽取前 10 页和主变卦完整章节，并渲染每页原图。助手实际逐页读文字、看原页、核对双栏后记录阅读覆盖；不得自动全选。验证器检查页集合、文件与来源指纹、阅读记录和疑字处理，**不能证明助手真正理解**。关键字无法确认时暂停受影响的判断，非关键疑字也须披露。

## 测试

没有原书时，可以验证起卦部分：

```bash
python3 -m unittest discover -s scripts -p test_skill.py -k CastingTests -v
```

安装依赖后，运行全部测试：

```bash
python3 scripts/test_skill.py
```

本地版本通过 11 项测试，涵盖 64 卦 × 64 种变爻掩码的 4096 种变化、项目卦例、阴阳定义切换、取辞主次、全书定位覆盖、双栏候选、渲染图有效性、未确认阅读拒绝、疑字披露和来源篡改拒绝。合成阅读勾选仅用于临时测试，不能作为真实阅读记录。

传统占筮是文化解读参考，不保证录用、具体时间或现实预测；现实选择仍结合实际条件和信息。仓库名称含“六爻”，不表示默认混用纳甲、六亲、世应或日月建体系。
