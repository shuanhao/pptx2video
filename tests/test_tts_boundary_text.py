"""Regression cases from MPU_WK04 slides 15, 22 and 26."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.tts_backend import SynthesisRequest
from src.tts_boundary_text import normalize_boundary_text
from src.tts_websocket import EdgeWebSocketBackend
from tests.test_tts_backends import FakeWebSocket, audio_frame, text_frame


def events(*texts):
    return [dict(text=text, offset_seconds=index * .5, duration_seconds=.4)
            for index, text in enumerate(texts)]


class BoundaryTextTests(unittest.TestCase):
    def test_complete_xml_entities_and_timestamps(self):
        source = 'Reliability & Management <tag> "quote" apostrophe\' 中文'
        original = events('Reliability &amp; Management', '&lt;tag&gt;',
                          '&quot;quote&quot;', 'apostrophe&#x27;', '&#20013;&#25991;')
        snapshot = copy.deepcopy(original)
        normalized = normalize_boundary_text(source, original)
        self.assertEqual([e['text'] for e in normalized],
                         ['Reliability & Management', '<tag>', '"quote"', "apostrophe'", '中文'])
        self.assertEqual(original, snapshot)
        self.assertEqual([(e['offset_seconds'], e['duration_seconds']) for e in normalized],
                         [(e['offset_seconds'], e['duration_seconds']) for e in original])
        self.assertEqual(normalized[0]['raw_text'], 'Reliability &amp; Management')
        self.assertEqual(normalize_boundary_text(source, normalized), normalized)

    def test_preserves_literal_entities_and_partial_html_names(self):
        source = 'A &amp; B &notliteral'
        original = events('A &amp;amp; B', '&notliteral')
        normalized = normalize_boundary_text(source, original)
        self.assertEqual([e['text'] for e in normalized], ['A &amp; B', '&notliteral'])
        self.assertEqual(normalize_boundary_text(source, normalized), normalized)

    def test_source_verified_fragment_and_following_anchor(self):
        source = '總結\n這一頁是 Week 4「Boot & System Startup」的總結。'
        original = events('總結', '這', '一頁', '是', 'Week', '4', 'Boot', '&', 'mp; Sy', 'Startup', '的', '總結')
        normalized = normalize_boundary_text(source, original)
        self.assertEqual(normalized[8]['text'], 'System')
        self.assertEqual(normalized[8]['raw_text'], 'mp; Sy')
        self.assertEqual(normalized[8]['offset_seconds'], original[8]['offset_seconds'])
        self.assertEqual(normalize_boundary_text(source, normalized), normalized)

    def test_unknown_mismatches_and_missing_anchors_remain_visible(self):
        for source, data in (
            ('Boot & System Startup', events('Boot', '&', 'unknown', 'Startup')),
            ('Boot & System Startup', events('Boot', '&', 'mp; Sy')),
            ('Boot & System skipped Startup', events('Boot', '&', 'mp; Sy', 'Startup')),
        ):
            self.assertEqual(normalize_boundary_text(source, data), data)

    def test_plain_text_backend_output_is_unchanged(self):
        original = events('Memory', 'Execution', '中文')
        self.assertEqual(normalize_boundary_text('Memory Execution 中文', original), original)

    def test_websocket_normalizes_before_returning_result(self):
        data = {'Metadata': [{'Type': 'WordBoundary', 'Data': {
            'Offset': 500000, 'Duration': 5000000, 'text': {'Text': 'Memory &amp; Execution'}}}]}
        ws = FakeWebSocket([audio_frame(), text_frame('audio.metadata', json.dumps(data)), text_frame('turn.end')])
        class Session:
            def __init__(self, **kwargs): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            def ws_connect(self, *args, **kwargs): return ws
        with tempfile.TemporaryDirectory() as tmp:
            result = EdgeWebSocketBackend(session_factory=Session).synthesize(
                SynthesisRequest('Memory & Execution', 'zh-TW-YunJheNeural'), Path(tmp) / 'audio.mp3')
        self.assertEqual(result.word_boundaries[0]['text'], 'Memory & Execution')
        self.assertEqual(result.metadata['boundary_text_normalization'], 'source-checked-xml-v1')

    def test_legacy_read_adapter_is_backend_scoped_and_does_not_rewrite_files(self):
        from src.subtitle_vtt import write_slide_vtt
        with tempfile.TemporaryDirectory() as tmp, patch(
                'src.subtitle_pipeline._measure_audio_duration_seconds', return_value=2.0):
            root = Path(tmp)
            audio = root / 'slide_001.mp3'
            timing = root / 'slide_001.wordboundaries.json'
            audio.write_bytes(b'original audio')
            timing.write_text(json.dumps(events('Memory &amp; Execution')), encoding='utf-8')
            before = timing.read_bytes()
            slides = [dict(slide_num=1, notes='Memory & Execution')]
            entry = dict(slide_num=1, audio_file=audio.name, word_boundaries_file=timing.name,
                         tts=dict(backend='edge-websocket', implementation_version='1'))
            paths = write_slide_vtt(slides, dict(slides=[entry]), root, root / 'vtt')
            self.assertEqual(len(paths), 1)
            self.assertEqual(timing.read_bytes(), before)
            self.assertEqual(audio.read_bytes(), b'original audio')
            # Other backends retain their existing validation behavior.
            entry['tts']['backend'] = 'edge-tts'
            with self.assertRaisesRegex(ValueError, 'Could not locate WordBoundary'):
                write_slide_vtt(slides, dict(slides=[entry]), root, root / 'other')
            # Unknown mismatches must still block the WebSocket backend's VTT.
            entry['tts']['backend'] = 'edge-websocket'
            timing.write_text(json.dumps(events('unmatched words')), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Could not locate WordBoundary'):
                write_slide_vtt(slides, dict(slides=[entry]), root, root / 'bad')


if __name__ == '__main__':
    unittest.main()
