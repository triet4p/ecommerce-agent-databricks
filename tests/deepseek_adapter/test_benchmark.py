from types import SimpleNamespace

from deepseek_adapter.benchmark import measure_stream, visible_text


def test_visible_text_excludes_reasoning_blocks():
    content = [
        {"type": "reasoning", "summary": []},
        {"type": "output_text", "text": "hello"},
        {"type": "text", "text": " world"},
    ]
    assert visible_text(content) == "hello world"


def test_measure_stream_records_first_visible_text():
    benchmark = measure_stream(
        [
            SimpleNamespace(content=[{"type": "reasoning"}]),
            SimpleNamespace(content=[{"type": "output_text", "text": "ok"}]),
        ]
    )
    assert benchmark.chunks == 2
    assert benchmark.visible_characters == 2
    assert benchmark.time_to_first_text_seconds is not None
