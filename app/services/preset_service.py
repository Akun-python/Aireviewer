from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.workflows.pipeline import BASE_CONSTRAINTS, BASE_EXPERT_VIEW


@dataclass(frozen=True)
class SectionExpectation:
    key: str
    label: str
    keywords: tuple[str, ...]
    min_paragraphs: int = 1


@dataclass(frozen=True)
class ReviewPreset:
    key: str
    label: str
    description: str
    expert_view: str
    default_constraints: tuple[str, ...] = field(default_factory=tuple)
    diagnostics_dimensions: tuple[str, ...] = field(default_factory=tuple)
    section_expectations: tuple[SectionExpectation, ...] = field(default_factory=tuple)
    skip_rules: tuple[str, ...] = field(default_factory=tuple)
    recommended_format_profile: str = "none"
    sample_use_cases: tuple[str, ...] = field(default_factory=tuple)
    system_prompt_scaffold: str = ""

    def to_public_dict(self) -> dict:
        payload = asdict(self)
        payload["default_constraints"] = list(self.default_constraints)
        payload["diagnostics_dimensions"] = list(self.diagnostics_dimensions)
        payload["skip_rules"] = list(self.skip_rules)
        payload["sample_use_cases"] = list(self.sample_use_cases)
        payload["section_expectations"] = [asdict(item) for item in self.section_expectations]
        return payload


_COMMON_DIAGNOSTICS = (
    "citation_reference_check",
    "section_structure_score",
    "terminology_consistency",
    "figure_table_caption_check",
    "logic_cohesion",
    "factual_numeric_risk",
)


PRESETS: dict[str, ReviewPreset] = {
    "general_academic": ReviewPreset(
        key="general_academic",
        label="通用学术论文/综述",
        description="适用于中文学术论文、综述、研究计划和一般性正式学术文稿。",
        expert_view="学术论文审阅专家",
        default_constraints=tuple(
            list(BASE_CONSTRAINTS)
            + [
                "优先检查摘要、引言、研究内容、创新点、结论与参考文献的完整性。",
                "重点关注术语一致性、引文格式、章节结构与论证连贯性。",
            ]
        ),
        diagnostics_dimensions=_COMMON_DIAGNOSTICS,
        section_expectations=(
            SectionExpectation("abstract", "摘要", ("摘要", "abstract"), 1),
            SectionExpectation("background", "研究背景/引言", ("引言", "研究背景", "前言"), 2),
            SectionExpectation("content", "研究内容/正文", ("研究内容", "研究方法", "正文", "分析"), 3),
            SectionExpectation("innovation", "创新点", ("创新", "创新之处", "特色"), 1),
            SectionExpectation("conclusion", "结论", ("结论", "结语", "总结"), 1),
            SectionExpectation("references", "参考文献", ("参考文献", "references"), 3),
        ),
        skip_rules=("不审阅目录页", "不修改图表题注编号", "对数值与年份采用保守修订策略"),
        recommended_format_profile="thesis_standard",
        sample_use_cases=("论文送审前精修", "综述文稿语言统一", "研究计划结构补强"),
        system_prompt_scaffold="从学术规范、论证结构、引用一致性和中文表达准确性四个维度进行审阅。",
    ),
    "social_science_fund": ReviewPreset(
        key="social_science_fund",
        label="国社科/课题申报/活页",
        description="适用于国社科、社科基金、课题申报书、活页与申报材料。",
        expert_view="课题申报书评审专家",
        default_constraints=tuple(
            list(BASE_CONSTRAINTS)
            + [
                "优先检查选题说明、选题依据、研究内容、创新点、预期成果、研究基础、参考文献等活页核心栏目。",
                "强调项目论证完整性、创新表达、学术价值与应用价值的平衡。",
            ]
        ),
        diagnostics_dimensions=_COMMON_DIAGNOSTICS,
        section_expectations=(
            SectionExpectation("topic", "选题说明", ("选题说明",), 1),
            SectionExpectation("justification", "选题依据", ("选题依据", "研究现状", "学术史"), 2),
            SectionExpectation("content", "研究内容", ("研究内容", "研究目标", "整体框架", "研究计划"), 3),
            SectionExpectation("innovation", "创新之处", ("创新之处", "创新", "特色"), 1),
            SectionExpectation("outcome", "预期成果", ("预期成果", "成果形式"), 1),
            SectionExpectation("foundation", "研究基础", ("研究基础", "前期成果"), 1),
            SectionExpectation("references", "参考文献", ("参考文献",), 3),
        ),
        skip_rules=("不弱化政策表述", "不删除已有章节标题", "对基金申报术语保持正式谨慎口吻"),
        recommended_format_profile="thesis_standard",
        sample_use_cases=("国社科活页打磨", "申报书结构补全", "创新点表述增强"),
        system_prompt_scaffold="从课题论证完整性、创新性、结构清晰度和基金申报规范性四个维度审阅。",
    ),
    "literature_review": ReviewPreset(
        key="literature_review",
        label="文献综述/研究现状梳理",
        description="适用于文献综述、学术史回顾、研究现状梳理类文稿。",
        expert_view="文献综述评审专家",
        default_constraints=tuple(
            list(BASE_CONSTRAINTS)
            + [
                "重点检查文献脉络梳理、作者年份格式、研究分组逻辑与综述结论。",
                "避免仅做语言润色而忽略文献组织结构和研究空白提炼。",
            ]
        ),
        diagnostics_dimensions=_COMMON_DIAGNOSTICS,
        section_expectations=(
            SectionExpectation("background", "研究背景", ("研究背景", "引言", "问题提出"), 1),
            SectionExpectation("history", "学术史/研究现状", ("研究现状", "文献综述", "学术史", "国内外研究"), 4),
            SectionExpectation("gap", "研究空白/评述", ("研究评述", "研究空白", "不足", "启示"), 2),
            SectionExpectation("references", "参考文献", ("参考文献",), 5),
        ),
        skip_rules=("不机械压缩文献综述篇幅", "对文献作者年份格式优先做一致性校正"),
        recommended_format_profile="thesis_standard",
        sample_use_cases=("综述章节重写", "文献引用规范化", "研究脉络重组"),
        system_prompt_scaffold="从文献组织、研究脉络、引文规范和综述结论四个维度审阅。",
    ),
}


def list_review_presets() -> list[dict]:
    return [preset.to_public_dict() for preset in PRESETS.values()]


def get_review_preset(preset_key: str | None) -> ReviewPreset:
    key = (preset_key or "").strip()
    if key in PRESETS:
        return PRESETS[key]
    return PRESETS["general_academic"]


def merge_constraints_with_preset(preset_key: str | None, constraints: list[str]) -> list[str]:
    preset = get_review_preset(preset_key)
    merged: list[str] = []
    seen: set[str] = set()
    for item in list(preset.default_constraints) + [str(value).strip() for value in constraints if str(value).strip()]:
        text = item.strip()
        if not text:
            continue
        normalized = text.replace(" ", "")
        if normalized in seen:
            continue
        seen.add(normalized)
        merged.append(text)
    return merged


def apply_preset_defaults(
    preset_key: str | None,
    *,
    expert_view: str | None,
    format_profile: str | None,
    constraints: list[str],
) -> tuple[str, str, list[str]]:
    preset = get_review_preset(preset_key)
    resolved_expert = (expert_view or "").strip() or preset.expert_view or BASE_EXPERT_VIEW
    resolved_format = (format_profile or "").strip() or preset.recommended_format_profile or "none"
    resolved_constraints = merge_constraints_with_preset(preset.key, constraints)
    return resolved_expert, resolved_format, resolved_constraints
