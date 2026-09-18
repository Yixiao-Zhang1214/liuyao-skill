#!/usr/bin/env python3
"""Deterministic casting under the user's majority-yin/yang convention."""
from __future__ import annotations

import argparse
from functools import lru_cache
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "references/book-index.json"
NORMALIZATION = str.maketrans({
    "爲": "为", "為": "为", "風": "风", "澤": "泽", "訟": "讼", "師": "师",
    "謙": "谦", "隨": "随", "蠱": "蛊", "臨": "临", "觀": "观", "賁": "贲",
    "剝": "剥", "復": "复", "無": "无", "頤": "颐", "過": "过", "離": "离",
    "恆": "恒", "遯": "遁", "壯": "壮", "晉": "晋", "損": "损", "歸": "归",
    "豐": "丰", "漸": "渐", "兌": "兑", "渙": "涣", "節": "节", "濟": "济",
})
TRIGRAM = {"天": "111", "泽": "110", "火": "101", "雷": "100",
           "风": "011", "水": "010", "山": "001", "地": "000"}
PURE = {"乾": "111", "兑": "110", "离": "101", "震": "100",
        "巽": "011", "坎": "010", "艮": "001", "坤": "000"}


def normalize(value: str) -> str:
    return re.sub(r"\s+", "", value).translate(NORMALIZATION).removesuffix("卦")


def validate_chapters(rows: list[dict]) -> None:
    if len(rows) != 64 or [r["sequence"] for r in rows] != list(range(1, 65)):
        raise ValueError("索引必须按文王卦序完整包含 64 卦")
    if len({r["title"] for r in rows}) != 64 or len({r["line_code_bottom_to_top"] for r in rows}) != 64:
        raise ValueError("卦名或六爻编码重复")
    covered = []
    for row in rows:
        title = row["title"]
        expected = PURE[title[0]] * 2 if "为" in title else TRIGRAM[title[1]] + TRIGRAM[title[0]]
        if row["line_code_bottom_to_top"] != expected:
            raise ValueError(f"索引卦名与编码不符：{title}")
        start, end = row["book_pages"]
        if start > end or row["pdf_pages"] != [start + 10, end + 10]:
            raise ValueError(f"页码映射不符：{title}")
        covered.extend(range(start + 10, end + 11))
    if covered != list(range(11, 147)):
        raise ValueError("章节索引未无遗漏地覆盖 PDF 11–146 页")


@lru_cache(maxsize=1)
def catalog() -> dict:
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    validate_chapters(data["chapters"])
    if data["pdf_pages"] != 146 or data["frontmatter_pdf_pages"] != list(range(1, 11)):
        raise ValueError("原书页数或前言范围不符")
    return data


def lookup(name: str) -> dict:
    key = normalize(name)
    matches = []
    for row in catalog()["chapters"]:
        title = row["title"]
        short = title.split("为")[0] if "为" in title else title[2:]
        if key in {title, short, row["symbol"], row["line_code_bottom_to_top"]}:
            matches.append(row)
    if len(matches) != 1:
        raise ValueError(f"卦名无法唯一识别：{name}")
    return dict(matches[0])


def line_name(row: dict, position: int) -> str:
    stem = "九" if row["line_code_bottom_to_top"][position - 1] == "1" else "六"
    if position == 1:
        return "初" + stem
    if position == 6:
        return "上" + stem
    return stem + "一二三四五六"[position - 1]


def evidence(row: dict, kind: str = "卦辞", position: int | None = None) -> dict:
    item = {"hexagram": row["title"], "kind": kind}
    if position is not None:
        item.update(position=position, line_name=line_name(row, position))
    return item


def selection(main: dict, changed: dict | None, moving: list[int] | None) -> dict:
    answer = {"primary": None, "secondary": [], "paired": [],
              "method": "项目约定：朱熹变占通行表；三动采用贞悔并看简化版"}
    if moving is None:
        answer.update(rule="动爻未知：仅解已知本卦卦辞，不视为零动", primary=evidence(main))
        return answer
    n = len(moving)
    if n == 0:
        answer.update(rule="零动：本卦卦辞", primary=evidence(main))
    elif n in (1, 2):
        primary = max(moving)
        answer.update(rule="一动：本卦该爻" if n == 1 else "两动：本卦两爻，较高者为主",
                      primary=evidence(main, "爻辞", primary),
                      secondary=[evidence(main, "爻辞", p) for p in moving if p != primary])
    elif n == 3:
        first, second = evidence(main), evidence(changed)
        first["role"], second["role"] = "贞", "悔"
        answer.update(rule="三动：本卦为贞、变卦为悔并看；不使用严格法前十后十细分",
                      paired=[first, second])
    elif n in (4, 5):
        unchanged = [p for p in range(1, 7) if p not in moving]
        answer.update(rule="四动：变卦两静爻，较低者为主" if n == 4 else "五动：变卦唯一静爻",
                      primary=evidence(changed, "爻辞", min(unchanged)),
                      secondary=[evidence(changed, "爻辞", p) for p in unchanged[1:]])
    else:
        kind = {"乾为天": "用九", "坤为地": "用六"}.get(main["title"], "卦辞")
        answer.update(rule="六动：乾用九、坤用六；另外 62 卦取变卦卦辞",
                      primary=evidence(main if kind != "卦辞" else changed, kind))
    return answer


def resolve(main: str, moving: list[int] | None = None, changed: str | None = None) -> dict:
    base = lookup(main)
    target = lookup(changed) if changed is not None else None
    code = base["line_code_bottom_to_top"]
    if moving is not None:
        if not isinstance(moving, list) or any(type(p) is not int or p not in range(1, 7) for p in moving):
            raise ValueError("动爻必须为 1–6 的整数列表")
        if len(set(moving)) != len(moving):
            raise ValueError("动爻位置不能重复")
        moving = sorted(moving)
        changed_code = "".join(str(1 - int(bit)) if i in moving else bit for i, bit in enumerate(code, 1))
        computed = lookup(changed_code)
        if target is not None and target["title"] != computed["title"]:
            raise ValueError(f"卦形冲突：这些动爻得到{computed['title']}，不是{target['title']}")
        target = computed
    elif target is not None:
        moving = [i for i, (a, b) in enumerate(zip(code, target["line_code_bottom_to_top"]), 1) if a != b]
    return {"main": base, "changed": target, "moving": moving,
            "mode": "guaci-only" if moving is None else "full",
            "order": "bottom-to-top", "selection": selection(base, target, moving)}


def cast_counts(counts: list[int]) -> dict:
    if not isinstance(counts, list) or len(counts) != 6:
        raise ValueError("必须提供自下而上六投，每投三面")
    if any(type(n) is not int or n not in range(4) for n in counts):
        raise ValueError("每投阳面数必须为 0–3 的整数")
    code = "".join("1" if n >= 2 else "0" for n in counts)
    moving = [i for i, n in enumerate(counts, 1) if n in (0, 3)]
    answer = resolve(code, moving)
    states = ["老阴", "少阴", "少阳", "老阳"]
    answer["lines_bottom_to_top"] = [
        {"position": i, "yang_faces": n, "yin_faces": 3 - n, "state": states[n],
         "drawing": "━━━━━━" if n >= 2 else "━━　━━", "moving": n in (0, 3),
         "marker": "○" if n == 3 else "×" if n == 0 else "",
         "main_line_name": line_name(answer["main"], i)}
        for i, n in enumerate(counts, 1)
    ]
    answer["convention"] = "用户指定：多数阴阳面成少爻，三同面成老爻；不是硬币数值求和法"
    return answer


def cast_tosses(text: str, positive: str = "yang") -> dict:
    if positive not in {"yang", "yin"}:
        raise ValueError("positive 只能为 yang 或 yin")
    tokens = [s.strip() for s in re.split(r"[,，、;；\n]+", text) if s.strip()]
    if len(tokens) != 6:
        raise ValueError("投掷记录必须恰为六投，自下而上")
    counts = []
    digits = str.maketrans({"一": "1", "二": "2", "两": "2", "兩": "2", "三": "3", "陽": "阳", "陰": "阴"})
    for token in tokens:
        compact = re.sub(r"\s+", "", token).translate(digits)
        parts = list(re.finditer(r"([123]?)(正|反|阳|阴)", compact))
        if "".join(m.group() for m in parts) != compact or not parts:
            raise ValueError(f"无法识别投掷记录：{token}")
        labels = {m.group(2) for m in parts}
        if labels & {"正", "反"} and labels & {"阳", "阴"}:
            raise ValueError("同一投请勿混用正反名称和阴阳名称")
        total, yang = 0, 0
        for item in parts:
            number = int(item.group(1) or 1)
            label = item.group(2)
            is_yang = label == "阳" or (label == "正" and positive == "yang") or (label == "反" and positive == "yin")
            total += number
            yang += number if is_yang else 0
        if total != 3:
            raise ValueError(f"每投必须三面：{token}")
        counts.append(yang)
    answer = cast_counts(counts)
    answer["face_definition"] = {"正": "阳" if positive == "yang" else "阴", "反": "阴" if positive == "yang" else "阳"}
    answer["tosses_bottom_to_top"] = tokens
    return answer


def parse_positions(value: str) -> list[int]:
    if value.lower() in {"none", "无", "静"}:
        return []
    try:
        return [int(s) for s in re.split(r"[,，、]", value)]
    except ValueError as error:
        raise ValueError("爻位用逗号分隔的 1–6；静卦用 none") from error


def main_cli() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    cast = sub.add_parser("cast")
    group = cast.add_mutually_exclusive_group(required=True)
    group.add_argument("--tosses")
    group.add_argument("--yang-counts", help="六个阳面数量，以逗号分隔，自下而上")
    cast.add_argument("--positive", choices=("yang", "yin"), default="yang")
    solve = sub.add_parser("resolve")
    solve.add_argument("--main", required=True)
    solve.add_argument("--moving", type=parse_positions)
    solve.add_argument("--changed")
    args = parser.parse_args()
    try:
        if args.command == "cast":
            result = cast_tosses(args.tosses, args.positive) if args.tosses is not None else cast_counts(parse_positions(args.yang_counts))
        else:
            result = resolve(args.main, args.moving, args.changed)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError) as error:
        parser.exit(2, f"错误：{error}\n")


if __name__ == "__main__":
    main_cli()
