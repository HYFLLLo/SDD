import json

from app.schema import (
    extract_json_block,
    flatten_paths,
    get_field_value,
    normalize_bbox,
    normalize_status,
    parse_bbox,
    parse_result,
)

FENCE = """模型输出如下：
```json
{"overall_status": "异常", "summary": "发现目标", "objects": [{"labelName": "挖掘机", "labelValue": "1台", "evidence": "画面中央", "bbox": [100, 100, 300, 300]}], "scene_analysis": {"image_quality": "清晰", "是否存在违规事件": "是"}}
```"""


def test_parse_result_strips_code_fence_and_maps_fields():
    r = parse_result(FENCE, "GLanLMM_V1.5", 1000, 500, None, "standard", None)
    assert r["parse_ok"] is True
    assert r["overall_status"] == "abnormal"
    assert r["summary"] == "发现目标"
    assert r["protocol_valid"] is True
    assert r["protocol_errors"] == []
    obj = r["objects"][0]
    assert obj["name"] == "挖掘机"
    assert obj["label_value"] == "1台"
    assert obj["evidence"] == "画面中央"
    assert obj["bbox"] == [100, 100, 300, 300]
    assert obj["bbox_normalized"] == [0.1, 0.2, 0.3, 0.6]


def test_parse_result_invalid_json_keeps_raw():
    raw = "抱歉，我无法判断。"
    r = parse_result(raw, "x", 100, 100, None, "standard", None)
    assert r["parse_ok"] is False
    assert r["overall_status"] is None
    assert r["objects"] == []
    assert r["raw"] == raw
    assert "protocol_valid" not in r


def test_parse_result_non_object_json_is_rejected():
    for text in ("[1, 2, 3]", '"just a string"', "null"):
        r = parse_result(text, "x", 100, 100, None, "standard", None)
        assert r["parse_ok"] is False, text


def test_parse_result_bbox_aliases():
    cases = [
        ("Vertex", "[10,20,30,40]"),
        ("vertex", [10, 20, 30, 40]),
        ("box", "10 20 30 40"),
        ("bounding_box", [10, 20, 30, 40]),
    ]
    for key, value in cases:
        payload = {"objects": [{"name": "car", key: value}]}
        r = parse_result(json.dumps(payload), "GLanLMM_V1.5", 100, 100, None, "standard", None)
        assert r["objects"][0]["bbox"] == [10, 20, 30, 40], key


def test_parse_result_skips_non_dict_objects_and_keeps_attributes():
    payload = {"objects": ["bad", {"name": "car", "bbox": [1, 1, 5, 5], "color": "red"}]}
    r = parse_result(json.dumps(payload), "x", 100, 100, None, "standard", None)
    assert len(r["objects"]) == 1
    assert r["objects"][0]["attributes"] == {"color": "red"}


def test_parse_result_custom_mode():
    payload = {
        "是否异常": "是",
        "缺陷列表": [{"类型": "裂纹", "位置": "[10,20,30,40]", "等级": "严重"}],
    }
    mapping = {
        "status_field": "是否异常",
        "objects_path": "缺陷列表",
        "name_field": "类型",
        "bbox_field": "位置",
    }
    r = parse_result(json.dumps(payload, ensure_ascii=False), "x", 1000, 1000, mapping, "custom", None)
    assert r["parse_ok"] is True
    assert r["overall_status"] == "是"
    assert r["objects"][0]["name"] == "裂纹"
    assert r["objects"][0]["bbox"] == [10, 20, 30, 40]
    assert r["objects"][0]["attributes"] == {"等级": "严重"}
    assert r["custom"] == payload


def test_parse_result_custom_mode_is_opt_in():
    payload = {"objects": [{"name": "car"}]}
    r = parse_result(json.dumps(payload), "x", 100, 100, None, "standard", None)
    assert "custom" not in r


def test_parse_result_protocol_errors_are_reported_not_fatal():
    r = parse_result(json.dumps({"overall_status": "正常"}), "x", 100, 100, None, "standard", None)
    assert r["parse_ok"] is True
    assert r["protocol_valid"] is False
    assert "缺少必填字段：scene_analysis" in r["protocol_errors"]
    assert "缺少必填字段：objects" in r["protocol_errors"]


def test_parse_result_scene_status_fallback():
    payload = {"objects": [], "scene_analysis": {"是否存在违规事件": "否"}}
    r = parse_result(json.dumps(payload, ensure_ascii=False), "x", 100, 100, None, "standard", None)
    assert r["overall_status"] == "normal"


def test_parse_result_custom_status_labels():
    payload = {"status": 1, "objects": []}
    r = parse_result(json.dumps(payload), "x", 100, 100, None, "standard", ["NG", "OK"])
    assert r["overall_status"] == "NG"
    r2 = parse_result(json.dumps({"status": "ok", "objects": []}), "x", 100, 100, None, "standard", ["NG", "OK"])
    assert r2["overall_status"] == "OK"


def test_normalize_status_keeps_unknown_value():
    assert normalize_status("待复核", [], None) == "待复核"
    assert normalize_status(None, [{"name": "x"}], None) == "abnormal"
    assert normalize_status(None, [], None) == "normal"


def test_normalize_bbox_coordinate_systems():
    assert normalize_bbox([0.1, 0.1, 0.5, 0.5], "x", 100, 100) == ([10, 10, 50, 50], [0.1, 0.1, 0.5, 0.5])
    assert normalize_bbox([100, 100, 500, 500], "GLanLMM_V1.6", 1000, 1000) == (
        [100, 100, 500, 500], [0.1, 0.1, 0.5, 0.5])
    assert normalize_bbox([10, 10, 50, 50], "GLanLMM_V1.5", 100, 100) == (
        [10, 10, 50, 50], [0.1, 0.1, 0.5, 0.5])
    assert normalize_bbox([300, 300, 100, 100], "GLanLMM_V1.5", 1000, 500) == (
        [100, 100, 300, 300], [0.1, 0.2, 0.3, 0.6])


def test_normalize_bbox_clamps_to_image_bounds():
    assert normalize_bbox([-10, -10, 50, 50], "GLanLMM_V1.5", 100, 100) == ([0, 0, 50, 50], [0.0, 0.0, 0.5, 0.5])
    assert normalize_bbox([5000, 5000, 6000, 6000], "GLanLMM_V1.6", 100, 100) == (
        [99, 99, 99, 99], [0.99, 0.99, 0.99, 0.99])


def test_parse_bbox_variants():
    assert parse_bbox("[10,20,30,40]") == [10.0, 20.0, 30.0, 40.0]
    assert parse_bbox("10 20 30 40") == [10.0, 20.0, 30.0, 40.0]
    assert parse_bbox([[1, 2, 3, 4], 9, 9, 9]) == [1.0, 2.0, 3.0, 4.0]
    assert parse_bbox([1, 2, 3]) is None
    assert parse_bbox("a,b,c,d") is None
    assert parse_bbox(None) is None


def test_extract_json_block_edge_cases():
    assert extract_json_block("") is None
    assert extract_json_block("no json here") is None
    assert extract_json_block('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert json.loads(extract_json_block('前缀 {"a": [1,2]} 后缀')) == {"a": [1, 2]}


REAL_DOUBLE_ENCODED = (
    '"{\\"scene_analysis\\": {\\"image_quality\\": \\"清晰\\", \\"是否存在目标/事件\\": \\"是\\"}, '
    '\\"objects\\": [{\\"labelName\\": \\"水边人员\\", \\"labelValue\\": \\"临边逗留\\", '
    '\\"evidence\\": \\"人员站立于水岸边缘\\", \\"bbox\\": [375,588,391,681]}], '
    '\\"analysis_summary\\": \\"画面中存在1名临边人员。\\"}"'
)


def test_extract_json_block_unwraps_double_encoded_json_string():
    """有的模型把整个 JSON 当成字符串再序列化一次（外层多一层引号 + 转义）。"""
    block = extract_json_block(REAL_DOUBLE_ENCODED)
    assert block is not None
    data = json.loads(block)
    assert data["objects"][0]["labelName"] == "水边人员"


def test_extract_json_block_unwraps_double_encoded_with_broken_tail_escape():
    """真实失败样本：外层引号包住整段 JSON，但结尾内部引号漏了反斜杠。"""
    body = (
        '{"objects": [{"labelName": "水边人员", "bbox": [1,2,3,4]}], '
        '"analysis_summary": "存在1名临边人员。"}'
    )
    escaped = body.replace('"', '\\"')
    raw = '"' + escaped + '"'
    # 去掉最后一个内部引号前的反斜杠，复现真实坏样本
    assert raw[-4:] == '\\"}"'
    broken = raw[:-4] + raw[-3:]
    block = extract_json_block(broken)
    assert block is not None, broken
    data = json.loads(block)
    assert data["objects"][0]["labelName"] == "水边人员"


def test_extract_json_block_repairs_duplicate_closing_bracket():
    """真实失败样本：bbox 行多打了一个 ]，导致 JSON 非法。"""
    raw = (
        "```json\n"
        '{\n  "scene_analysis": {"image_quality": "清晰", "是否存在目标/事件": "是"},\n'
        '  "objects": [\n    {\n      "labelName": "水边人员",\n'
        '      "labelValue": "临边逗留",\n      "evidence": "临边区域人员",\n'
        '      "bbox": [213,341,232,386]]\n    }\n  ],\n'
        '  "analysis_summary": "发现一名临边人员。"\n}\n```\n'
    )
    block = extract_json_block(raw)
    assert block is not None
    data = json.loads(block)
    assert data["objects"][0]["bbox"] == [213, 341, 232, 386]


def test_parse_result_reports_parse_stage_not_failure_for_repaired_json():
    r = parse_result(REAL_DOUBLE_ENCODED, "x", 1000, 1000, None, "standard", None)
    assert r["parse_ok"] is True
    assert r["objects"][0]["name"] == "水边人员"


def test_get_field_value_paths():
    data = {"objects": [{"name": "a"}, {"name": "b"}], "a": {"b": 1}}
    assert get_field_value(data, "objects[].name") == ["a", "b"]
    assert get_field_value(data, "a.b") == 1
    assert get_field_value(data, "missing.path") is None
    assert get_field_value({"tags": ["x"]}, "tags") == ["x"]


def test_flatten_paths_and_limits():
    data = {"a": 1, "b": {"c": 2}, "objs": [{"n": 1}], "_meta": {"z": 9}, "raw": "x", "tags": ["t1"]}
    assert flatten_paths(data, 4, 200) == ["a", "b.c", "objs[].n", "tags[]"]
    assert flatten_paths({"a": {"b": 2}}, 0, 200) == []
    assert flatten_paths({"a": {"b": 1, "c": {"d": 2}}}, 4, 1) == ["a.b"]


def test_flatten_paths_defaults_are_usable():
    assert flatten_paths({"a": 1}) == ["a"]
