import tempfile
import unittest
from pathlib import Path

from src.tts import WORD_BOUNDARY_TICKS_PER_SECOND, synthesize_with_word_boundaries


class FakeCommunicate:
    """Stand-in for edge_tts.Communicate - yields canned chunks instead of
    making a real network call, the same dependency-injection approach
    generate_audio_files() uses for its ``generator`` parameter.
    """

    def __init__(self, chunks, **kwargs):
        self._chunks = chunks
        self.init_kwargs = kwargs

    async def stream(self):
        for chunk in self._chunks:
            yield chunk


def _factory(chunks, captured_kwargs_holder):
    def factory(**kwargs):
        captured_kwargs_holder.append(kwargs)
        return FakeCommunicate(chunks, **kwargs)

    return factory


class TtsWordBoundariesTests(unittest.TestCase):
    def test_returns_word_boundaries_converted_to_seconds(self):
        # 5,000,000 ticks / 10,000,000 ticks-per-second = 0.5s - chosen so
        # the tick -> second division is easy to eyeball in the assertion.
        chunks = [
            {"type": "audio", "data": b"fake-mp3-bytes-1"},
            {"type": "WordBoundary", "text": "Hello", "offset": 0, "duration": 5_000_000},
            {"type": "audio", "data": b"fake-mp3-bytes-2"},
            {"type": "WordBoundary", "text": "world", "offset": 5_000_000, "duration": 7_500_000},
        ]
        captured_kwargs = []

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "slide_001.mp3"

            events = synthesize_with_word_boundaries(
                "Hello world",
                output_path,
                voice="en-US-AriaNeural",
                communicate_factory=_factory(chunks, captured_kwargs),
            )

        self.assertEqual(
            events,
            [
                {"text": "Hello", "offset_seconds": 0.0, "duration_seconds": 0.5},
                {"text": "world", "offset_seconds": 0.5, "duration_seconds": 0.75},
            ],
        )

    def test_writes_audio_chunks_to_output_path_in_order(self):
        chunks = [
            {"type": "audio", "data": b"first-"},
            {"type": "WordBoundary", "text": "x", "offset": 0, "duration": 1_000_000},
            {"type": "audio", "data": b"second"},
        ]

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "nested" / "slide_001.mp3"

            synthesize_with_word_boundaries(
                "x",
                output_path,
                voice="en-US-AriaNeural",
                communicate_factory=_factory(chunks, []),
            )

            self.assertTrue(output_path.exists())
            self.assertEqual(output_path.read_bytes(), b"first-second")

    def test_ignores_sentence_boundary_chunks(self):
        # edge-tts can also emit "SentenceBoundary" chunks (it's the
        # default boundary type when none is requested). This function
        # asks for boundary="WordBoundary" specifically, but a fake/future
        # edge-tts version could still send other types mixed in - only
        # "WordBoundary" chunks should end up in the returned list.
        chunks = [
            {"type": "SentenceBoundary", "text": "Hello world", "offset": 0, "duration": 12_500_000},
            {"type": "WordBoundary", "text": "Hello", "offset": 0, "duration": 5_000_000},
            {"type": "audio", "data": b"fake"},
        ]

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "slide_001.mp3"

            events = synthesize_with_word_boundaries(
                "Hello world",
                output_path,
                voice="en-US-AriaNeural",
                communicate_factory=_factory(chunks, []),
            )

            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["text"], "Hello")

    def test_passes_boundary_word_and_voice_rate_pitch_to_factory(self):
        captured_kwargs = []

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "slide_001.mp3"

            synthesize_with_word_boundaries(
                "some text",
                output_path,
                voice="zh-TW-YunJheNeural",
                rate="-10%",
                pitch="+0Hz",
                communicate_factory=_factory([], captured_kwargs),
            )

        self.assertEqual(len(captured_kwargs), 1)
        kwargs = captured_kwargs[0]
        self.assertEqual(kwargs["text"], "some text")
        self.assertEqual(kwargs["voice"], "zh-TW-YunJheNeural")
        self.assertEqual(kwargs["rate"], "-10%")
        self.assertEqual(kwargs["pitch"], "+0Hz")
        self.assertEqual(kwargs["boundary"], "WordBoundary")

    def test_returns_empty_list_when_no_boundary_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "slide_001.mp3"

            events = synthesize_with_word_boundaries(
                "",
                output_path,
                voice="en-US-AriaNeural",
                communicate_factory=_factory([{"type": "audio", "data": b""}], []),
            )

            self.assertEqual(events, [])
            self.assertTrue(output_path.exists())

    def test_falls_back_to_no_boundary_kwarg_when_factory_rejects_it(self):
        # Simulates edge-tts < 7.2.0, where Communicate.__init__ doesn't
        # accept a "boundary" keyword at all and raises TypeError if given
        # one (confirmed by installing older releases and inspecting the
        # real signature - see the docstring in tts.py). The function
        # should retry once without "boundary" rather than propagating the
        # TypeError, and still return whatever WordBoundary events the
        # (older-style) factory yields.
        chunks = [
            {"type": "audio", "data": b"fake"},
            {"type": "WordBoundary", "text": "Hi", "offset": 0, "duration": 1_000_000},
        ]
        captured_kwargs = []

        def factory(**kwargs):
            if "boundary" in kwargs:
                raise TypeError("Communicate.__init__() got an unexpected keyword argument 'boundary'")
            captured_kwargs.append(kwargs)
            return FakeCommunicate(chunks, **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "slide_001.mp3"

            events = synthesize_with_word_boundaries(
                "Hi",
                output_path,
                voice="en-US-AriaNeural",
                communicate_factory=factory,
            )

        self.assertEqual(len(captured_kwargs), 1)
        self.assertNotIn("boundary", captured_kwargs[0])
        self.assertEqual(events, [{"text": "Hi", "offset_seconds": 0.0, "duration_seconds": 0.1}])

    def test_ticks_per_second_constant_matches_documented_unit(self):
        # Guards against silently changing the conversion constant without
        # updating the (extensively commented) reasoning above it - the
        # value must stay in sync with what edge_tts.communicate actually
        # reports (100-nanosecond ticks), which was confirmed by reading
        # its source, not its public docs.
        self.assertEqual(WORD_BOUNDARY_TICKS_PER_SECOND, 10_000_000)


if __name__ == "__main__":
    unittest.main()
