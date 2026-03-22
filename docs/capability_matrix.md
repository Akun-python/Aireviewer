# Capability Matrix

| Capability | React | Streamlit | API | CLI | Win32 Word Required | python-docx Fallback |
| --- | --- | --- | --- | --- | --- | --- |
| 智能校稿 | Yes | Yes | Yes | Yes | Preferred | Yes |
| 学术诊断 JSON | Yes | Yes | Yes | Yes | No | Yes |
| 课题报告生成 | Yes | Yes | Yes | No | Preferred | Partial |
| 完善已有报告 | Yes | Yes | Yes | No | Yes | No |
| 多章节整合 | Yes | Yes | Yes | No | Yes | No |
| 运行中心 / artifacts | Yes | Streamlit session history | Yes | No | No | Yes |
| Word 原生修订痕迹 | Indirect via backend | Yes | Yes | Yes | Yes | No |
| 高保真目录 / 多级编号 / 排版 | Indirect via backend | Yes | Yes | No | Yes | Limited |
| 图表题注自动化 | Indirect via backend | Yes | Yes | No | Yes | Limited |

## Notes

- When Win32 Word is available, the project can preserve higher-fidelity revision traces, TOC generation, formatting, and chapter integration.
- Without Win32 Word, diagnostics and most document-structure analysis can still run.
- `python-docx` fallback is suitable for lightweight revision and inspection, but not for full Word-native revision markup or high-fidelity formatting output.
