from app.core.ocr import (
    _build_manual_template_bundle,
    _build_bilingual_text,
    _build_page_semantics,
    _build_page_from_layout_result,
    _extract_spec_table_rows,
    _extract_fasteners_from_line,
    _extract_materials_from_line,
    _extract_procedures,
    _extract_specs,
    _extract_tools_from_line,
    _is_specific_step_line,
    _merge_step_lines,
)


def test_extract_specs_keeps_range_and_subject():
    specs = _extract_specs("\u540e\u5236\u52a8\u76d8\u87ba\u6813\uff1a10.0-16.0N\xb7m")
    assert specs
    assert specs[0]["value"] == "10.0-16.0"
    assert specs[0]["label"] == "\u540e\u5236\u52a8\u76d8\u87ba\u6813\u626d\u77e9"


def test_extract_tools_fasteners_and_materials_from_line():
    line = "\u4f7f\u7528\u4e13\u7528\u5de5\u5177\u548c M8 \u5185\u516d\u89d2\u6273\u624b\u62c6\u4e0b\u673a\u6cb9\u6ee4\u6e05\u5668\u56fa\u5b9a\u87ba\u6813\uff0c\u5e76\u66f4\u6362\u673a\u6cb9 1.2L\u3002"
    tools = _extract_tools_from_line(line)
    fasteners = _extract_fasteners_from_line(line)
    materials = _extract_materials_from_line(line)

    assert "M8 \u5185\u516d\u89d2\u6273\u624b" in tools
    assert any(item["size"] == "M8" and item["drive_type"] == "\u5185\u516d\u89d2" for item in fasteners)
    assert any(item["name"] == "\u673a\u6cb9\u6ee4\u6e05\u5668" for item in materials)
    assert any(item["name"] == "\u673a\u6cb9" and item["value"] == "1.2" and item["unit"] == "L" for item in materials)


def test_specific_step_filter_rejects_generic_entries():
    assert not _is_specific_step_line("\u5b89\u88c5")
    assert not _is_specific_step_line("\u68c0\u67e5")
    assert _is_specific_step_line("\u62c6\u4e0b\u653e\u6cb9\u87ba\u6813\u5e76\u6392\u51fa\u673a\u6cb9")


def test_merge_step_lines_combines_detail_lines():
    lines = [
        "1. \u62c6\u4e0b\u653e\u6cb9\u87ba\u6813",
        "\u4f7f\u7528 M8 \u5185\u516d\u89d2\u6273\u624b\u64cd\u4f5c",
        "\u6309 24N\xb7m \u56de\u88c5\u5e76\u7d27\u56fa",
        "2. \u5b89\u88c5",
    ]
    merged = _merge_step_lines(lines)
    assert len(merged) == 1
    assert "M8" in merged[0]
    assert "24N\xb7m" in merged[0]


def test_merge_step_lines_supports_multiple_numbering_formats():
    lines = [
        "Step 1: Remove drain bolt",
        "Use M8 Allen wrench",
        "Torque: 24N\xb7m after installation",
        "B) Fill engine oil 1.2L",
        "Check for leaks",
    ]
    merged = _merge_step_lines(lines)
    assert len(merged) == 2
    assert "Remove drain bolt" in merged[0]
    assert "24N\xb7m" in merged[0]
    assert "Fill engine oil 1.2L" in merged[1]


def test_extract_specs_supports_table_like_lines():
    specs = _extract_specs("Drain bolt torque | 24 N\xb7m\nEngine oil capacity    1.2 L")
    assert any(item["type"] == "torque" and item["value"] == "24" for item in specs)
    assert any(item["type"] == "capacity" and item["value"] == "1.2" for item in specs)


def test_extract_spec_table_rows_supports_header_and_values():
    rows = _extract_spec_table_rows(
        "Item | Standard value | Limit value | Tool | Note\n"
        "Valve clearance | 0.10-0.20 mm | 0.30 mm | Feeler gauge | Cold engine\n"
    )
    assert rows
    assert rows[0]["item"] == "Valve clearance"
    assert rows[0]["standard_value"] == "0.10-0.20 mm"
    assert rows[0]["limit_value"] == "0.30 mm"
    assert rows[0]["tool"] == "Feeler gauge"


def test_extract_spec_table_rows_supports_cn_alias_headers():
    rows = _extract_spec_table_rows(
        "检查项目 | 规定值 | 使用限度 | 专用工具 | 备注 | 适用车型\n"
        "气门间隙 | 0.10-0.20 mm | 0.30 mm | 塞尺 | 冷机 | DR250\n"
    )
    assert rows
    assert rows[0]["item"] == "气门间隙"
    assert rows[0]["standard_value"] == "0.10-0.20 mm"
    assert rows[0]["limit_value"] == "0.30 mm"
    assert rows[0]["tool"] == "塞尺"
    assert rows[0]["note"] == "冷机"
    assert rows[0]["model"] == "DR250"


def test_extract_spec_table_rows_supports_abbreviation_headers():
    rows = _extract_spec_table_rows(
        "ITEM | STD | LIMIT | SST | REMARKS | MODEL\n"
        "Chain slack | 20-30 mm | 40 mm | Ruler | Side stand | DR250\n"
    )
    assert rows
    assert rows[0]["item"] == "Chain slack"
    assert rows[0]["standard_value"] == "20-30 mm"
    assert rows[0]["limit_value"] == "40 mm"
    assert rows[0]["tool"] == "Ruler"
    assert rows[0]["note"] == "Side stand"
    assert rows[0]["model"] == "DR250"


def test_extract_spec_table_rows_supports_japanese_alias_headers():
    rows = _extract_spec_table_rows(
        "項目 | 基準値 | サービスリミット | 専用工具 | 備考 | 適用車種\n"
        "バルブクリアランス | 0.10-0.20 mm | 0.30 mm | シックネスゲージ | 冷間 | DR250\n"
    )
    assert rows
    assert rows[0]["item"] == "バルブクリアランス"
    assert rows[0]["standard_value"] == "0.10-0.20 mm"
    assert rows[0]["limit_value"] == "0.30 mm"
    assert rows[0]["tool"] == "シックネスゲージ"
    assert rows[0]["note"] == "冷間"
    assert rows[0]["model"] == "DR250"


def test_extract_procedures_supports_bullets_letters_and_english_verbs():
    text = (
        "A) Remove drain bolt\n"
        "Use M8 Allen wrench\n"
        "Torque: 24N\xb7m after installation\n"
        "\u2022 Fill engine oil 1.2L\n"
        "Check for leaks\n"
    )
    procedures = _extract_procedures(text)
    assert len(procedures) == 2
    assert procedures[0]["instruction_original"].startswith("A) Remove drain bolt")
    assert procedures[0]["required_tools"]
    assert procedures[1]["instruction"].startswith("Fill engine oil 1.2L")
    assert procedures[0]["instruction_zh"]


def test_build_bilingual_text_translates_repair_terms():
    result = _build_bilingual_text("Remove drain bolt")
    assert result["original"] == "Remove drain bolt"
    assert result["zh"] == "拆下 放油螺栓"

    jp_result = _build_bilingual_text("ドレンボルト締付トルク")
    assert jp_result["zh"] == "放油螺栓扭矩"


def test_build_page_semantics_detects_layout_and_strategy():
    procedure_semantics = _build_page_semantics(
        "Step 1: Remove drain bolt\nUse M8 Allen wrench\nTorque: 24N\xb7m after installation\nStep 2: Fill engine oil 1.2L\n"
    )
    assert procedure_semantics["layout_profile"]["layout_mode"] == "numbered_steps"
    assert procedure_semantics["extraction_strategy"] == "procedure_first"

    spec_semantics = _build_page_semantics(
        "Drain bolt torque | 24 N\xb7m\nEngine oil capacity    1.2 L\nBrake fluid : DOT4\n"
    )
    assert spec_semantics["layout_profile"]["layout_mode"] == "table_dense"
    assert spec_semantics["extraction_strategy"] == "spec_table_first"


def test_build_page_from_layout_result_segments_mixed_page_content():
    page = _build_page_from_layout_result(
        {
            "markdown": {
                "text": (
                    "# Engine oil service\n"
                    "Drain bolt torque | 24 N\xb7m\n"
                    "Engine oil capacity    1.2 L\n"
                    "Step 1: Remove drain bolt\n"
                    "Use M8 Allen wrench\n"
                    "Step 2: Fill engine oil 1.2L\n"
                )
            }
        },
        1,
    )
    assert page["content_segments"]
    assert any(item["role"] == "spec" for item in page["content_segments"])
    assert any(item["role"] == "procedure" for item in page["content_segments"])
    assert any(item["type"] == "torque" for item in page["specs"])
    assert page["spec_table_rows"]
    assert len(page["procedures"]) >= 2


def test_extract_procedures_ignores_generic_steps():
    text = (
        "# \u53d1\u52a8\u673a\u673a\u6cb9\u66f4\u6362\n"
        "1. \u62c6\u4e0b\u653e\u6cb9\u87ba\u6813\n"
        "\u4f7f\u7528 M8 \u5185\u516d\u89d2\u6273\u624b\u64cd\u4f5c\n"
        "\u6309 24N\xb7m \u56de\u88c5\u5e76\u7d27\u56fa\n"
        "2. \u5b89\u88c5\n"
        "3. \u52a0\u6ce8\u673a\u6cb9 1.2L\n"
    )
    procedures = _extract_procedures(text)
    assert len(procedures) == 2
    assert all(item["instruction"] != "\u5b89\u88c5" for item in procedures)
    assert "24N\xb7m" in procedures[0]["instruction"]
    assert procedures[0]["instruction_original"].startswith("1. \u62c6\u4e0b\u653e\u6cb9\u87ba\u6813")
    assert procedures[0]["action_type"] == "removal"
    assert procedures[0]["target_component"] == "\u653e\u6cb9\u87ba\u6813"
    assert procedures[0]["preconditions"]
    assert procedures[0]["setup_conditions"]
    assert procedures[0]["acceptance_checks"]
    assert procedures[0]["reassembly_requirements"]
    assert procedures[0]["common_failure_modes"]
    assert procedures[0]["executor_role"]
    assert procedures[0]["verification_role"]
    assert procedures[0]["record_requirements"]
    assert procedures[0]["step_purpose"]
    assert procedures[0]["input_requirements"]
    assert procedures[0]["completion_definition"]
    assert procedures[0]["output_results"]
    assert procedures[1]["action_type"] == "filling"
    assert procedures[1]["criticality"] in {"critical", "major"}


def test_build_manual_template_bundle_contains_technician_view():
    result = {
        "page_count": 1,
        "sections": [{"title": "\u53d1\u52a8\u673a\u673a\u6cb9\u66f4\u6362"}],
        "specs": [
            {
                "type": "torque",
                "label": "\u653e\u6cb9\u87ba\u6813\u626d\u77e9",
                "value": "24",
                "unit": "N\xb7m",
                "source_text": "\u653e\u6cb9\u87ba\u6813\uff1a24N\xb7m",
            },
            {
                "type": "capacity",
                "label": "\u673a\u6cb9\u5bb9\u91cf",
                "value": "1.2",
                "unit": "L",
                "source_text": "\u673a\u6cb9\u5bb9\u91cf\uff1a1.2L",
            },
        ],
        "procedures": [],
        "pages": [
            {
                "page_number": 1,
                "page_type": "procedure",
                "page_type_reason": "heuristic",
                "summary": "\u53d1\u52a8\u673a\u673a\u6cb9\u66f4\u6362",
                "text": (
                    "# \u53d1\u52a8\u673a\u673a\u6cb9\u66f4\u6362\n"
                    "1. \u62c6\u4e0b\u653e\u6cb9\u87ba\u6813\n"
                    "\u4f7f\u7528 M8 \u5185\u516d\u89d2\u6273\u624b\u64cd\u4f5c\n"
                    "\u6309 24N\xb7m \u56de\u88c5\u5e76\u7d27\u56fa\n"
                    "3. \u52a0\u6ce8\u673a\u6cb9 1.2L\n"
                ),
            }
        ],
    }

    bundle = _build_manual_template_bundle(result)
    technician_view = bundle["normalized_manual"]["technician_view"]

    assert technician_view["quick_reference"]["torque"]
    assert technician_view["quick_reference"]["fluids"]
    assert technician_view["quick_reference"]["tools"]
    assert len(technician_view["step_cards"]) == 2
    assert technician_view["step_cards"][0]["instruction_original"].startswith("1. \u62c6\u4e0b\u653e\u6cb9\u87ba\u6813")
    assert technician_view["step_cards"][0]["action_type"] == "removal"
    assert technician_view["step_cards"][0]["target_component"] == "\u653e\u6cb9\u87ba\u6813"
    assert technician_view["step_cards"][0]["instruction_zh"] is None
    assert technician_view["step_cards"][0]["preconditions"]
    assert technician_view["step_cards"][0]["reassembly_requirements"]
    assert technician_view["step_cards"][0]["control_points"]
    assert technician_view["step_cards"][0]["executor_role"]
    assert technician_view["step_cards"][0]["verification_role"]
    assert technician_view["step_cards"][0]["record_requirements"]
    assert technician_view["step_cards"][0]["step_purpose"]
    assert technician_view["step_cards"][0]["input_requirements"]
    assert technician_view["step_cards"][0]["completion_definition"]
    assert technician_view["step_cards"][0]["output_results"]
    assert technician_view["quick_reference"]["critical_steps"]
    assert bundle["normalized_manual"]["traceability"]["page_summaries"][0]["layout_profile"]
    assert bundle["normalized_manual"]["traceability"]["page_summaries"][0]["extraction_strategy"]
    assert bundle["normalized_manual"]["traceability"]["page_summaries"][0]["content_segments"]
    assert bundle["normalized_manual"]["traceability"]["page_summaries"][0]["spec_table_rows"] is not None
    assert bundle["normalized_manual"]["specifications"]["spec_table_rows"] is not None


def test_build_manual_template_bundle_adds_bilingual_fields_for_english_manual():
    result = {
        "page_count": 1,
        "sections": [{"title": "Engine oil service"}],
        "specs": [
            {
                "type": "torque",
                "label": "Drain bolt torque",
                "value": "24",
                "unit": "N·m",
                "source_text": "Drain bolt torque | 24 N·m",
            }
        ],
        "procedures": [],
        "pages": [
            {
                "page_number": 1,
                "page_type": "procedure",
                "page_type_reason": "heuristic",
                "summary": "Engine oil service",
                "text": (
                    "Step 1: Remove drain bolt\n"
                    "Use M8 Allen wrench\n"
                    "Torque: 24N·m after installation\n"
                ),
                "spec_table_rows": [
                    {
                        "item": "Drain bolt torque",
                        "standard_value": "24 N·m",
                        "tool": "Allen wrench",
                        "note": "Cold engine",
                    }
                ],
            }
        ],
    }

    bundle = _build_manual_template_bundle(result)
    manual = bundle["normalized_manual"]
    assert manual["document_profile"]["language"] == "en"
    assert manual["technician_view"]["step_cards"][0]["instruction_zh"]
    assert manual["technician_view"]["quick_reference"]["tools"]
    assert manual["specifications"]["torque_specs"][0]["label_zh"] == "放油螺栓扭矩"
    assert manual["specifications"]["spec_table_rows"][0]["item_zh"] == "放油螺栓扭矩"
