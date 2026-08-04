import json
import ssl
import tempfile
import unittest
from pathlib import Path

from src.exceptions import TTSGenerationError
from src.tts import generate_audio_files


class FakeCommunicate:
    """Stand-in for edge_tts.Communicate - yields canned chunks instead of
    making a real network call. Same shape as the fake used in
    tests/test_tts_word_boundaries.py, duplicated here (rather than
    imported) so this test file stays self-contained.
    """

    def __init__(self, chunks, **kwargs):
        self._chunks = chunks

    async def stream(self):
        for chunk in self._chunks:
            yield chunk


def _factory(chunks):
    def factory(**kwargs):
        return FakeCommunicate(chunks, **kwargs)

    return factory


class TtsGeneratorTests(unittest.TestCase):
    def test_generate_audio_files_skips_slides_without_notes(self):
        slides = [
            {"slide_num": 1, "title": "Intro", "notes": "Hello there"},
            {"slide_num": 2, "title": "No notes", "notes": None},
            {"slide_num": 3, "title": "Outro", "notes": "Thanks for watching"},
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            def fake_generator(text, output_path, voice):
                output_path.write_bytes(b"fake-audio")

            manifest = generate_audio_files(
                slides,
                output_dir,
                voice="en-US-AriaNeural",
                generator=fake_generator,
            )

            self.assertEqual(
                [entry["audio_file"] for entry in manifest["slides"]],
                ["slide_001.mp3", "slide_003.mp3"],
            )
            self.assertTrue((output_dir / "slide_001.mp3").exists())
            self.assertTrue((output_dir / "slide_003.mp3").exists())
            self.assertFalse((output_dir / "slide_002.mp3").exists())
            # A custom generator isn't guaranteed to produce timing data, so
            # no sidecar file is written and the manifest says so explicitly
            # rather than omitting the key.
            self.assertEqual(
                [entry["word_boundaries_file"] for entry in manifest["slides"]],
                [None, None],
            )
            self.assertFalse((output_dir / "slide_001.wordboundaries.json").exists())

    def test_generate_audio_files_clamps_negative_max_retries_instead_of_skipping(self):
        # Regression test: range(1, max_retries + 2) is empty when
        # max_retries is negative (e.g. -1 -> range(1, 1)), which used to
        # mean the generator was never called at all, yet the slide was
        # still recorded in the manifest as if audio had been generated for
        # it. max_retries must be clamped to 0 so the generator always runs
        # at least once.
        slides = [{"slide_num": 1, "title": "Intro", "notes": "Hello there"}]
        calls = []

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            def fake_generator(text, output_path, voice):
                calls.append(output_path)
                output_path.write_bytes(b"fake-audio")

            manifest = generate_audio_files(
                slides,
                output_dir,
                voice="en-US-AriaNeural",
                generator=fake_generator,
                max_retries=-1,
            )

            self.assertEqual(len(calls), 1)
            self.assertTrue((output_dir / "slide_001.mp3").exists())
            self.assertEqual(
                [entry["audio_file"] for entry in manifest["slides"]],
                ["slide_001.mp3"],
            )

    def test_generate_audio_files_reports_progress(self):
        slides = [
            {"slide_num": 1, "title": "Intro", "notes": "Hello there"},
            {"slide_num": 2, "title": "No notes", "notes": None},
            {"slide_num": 3, "title": "Middle", "notes": "Some content"},
            {"slide_num": 4, "title": "Outro", "notes": "Thanks for watching"},
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            def fake_generator(text, output_path, voice):
                output_path.write_bytes(b"fake-audio")

            progress_calls = []

            def track_progress(current, total, slide_num):
                progress_calls.append((current, total, slide_num))

            generate_audio_files(
                slides,
                output_dir,
                voice="en-US-AriaNeural",
                generator=fake_generator,
                progress_callback=track_progress,
            )

            # Only slides with notes count towards the total (3 of them),
            # and the callback fires once per generated file, in order.
            self.assertEqual(progress_calls, [(1, 3, 1), (2, 3, 3), (3, 3, 4)])

    def test_generate_audio_files_works_without_progress_callback(self):
        slides = [{"slide_num": 1, "title": "Intro", "notes": "Hello there"}]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            def fake_generator(text, output_path, voice):
                output_path.write_bytes(b"fake-audio")

            # Should not raise even though no progress_callback is passed.
            manifest = generate_audio_files(
                slides,
                output_dir,
                voice="en-US-AriaNeural",
                generator=fake_generator,
            )
            self.assertEqual(len(manifest["slides"]), 1)

    def test_generate_audio_files_wraps_generator_failure_with_slide_context(self):
        slides = [
            {"slide_num": 1, "title": "Intro", "notes": "Hello there"},
            {"slide_num": 2, "title": "Boom", "notes": "This one fails"},
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            def flaky_generator(text, output_path, voice):
                if "fails" in text:
                    raise ConnectionError("network is down")
                output_path.write_bytes(b"fake-audio")

            with self.assertRaises(TTSGenerationError) as ctx:
                generate_audio_files(
                    slides,
                    output_dir,
                    voice="en-US-AriaNeural",
                    generator=flaky_generator,
                    # ConnectionError is retryable (see test_retries_* below
                    # for that behavior) - use a zero delay here since this
                    # test only cares about the final failure, not retrying.
                    retry_delay_seconds=0,
                )

            # The error message should say which slide failed, and the
            # original exception should still be reachable via chaining.
            self.assertIn("slide 2", str(ctx.exception))
            self.assertIsInstance(ctx.exception.__cause__, ConnectionError)

    def test_generate_audio_files_hints_at_ffmpeg_for_file_not_found(self):
        slides = [{"slide_num": 1, "title": "Intro", "notes": "Hello there"}]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            def missing_ffmpeg_generator(text, output_path, voice):
                raise FileNotFoundError("ffmpeg not found")

            with self.assertRaises(TTSGenerationError) as ctx:
                generate_audio_files(
                    slides,
                    output_dir,
                    voice="en-US-AriaNeural",
                    generator=missing_ffmpeg_generator,
                )

            self.assertIn("ffmpeg", str(ctx.exception))

    def test_generate_audio_files_retries_transient_error_then_succeeds(self):
        slides = [{"slide_num": 1, "title": "Intro", "notes": "Hello there"}]
        call_count = {"n": 0}

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            def flaky_then_ok_generator(text, output_path, voice):
                call_count["n"] += 1
                if call_count["n"] < 3:
                    raise ConnectionError("temporary network blip")
                output_path.write_bytes(b"fake-audio")

            retry_events = []

            def track_retry(attempt, max_retries, slide_num, exc):
                retry_events.append((attempt, max_retries, slide_num))

            manifest = generate_audio_files(
                slides,
                output_dir,
                voice="en-US-AriaNeural",
                generator=flaky_then_ok_generator,
                retry_delay_seconds=0,
                on_retry=track_retry,
            )

            # Failed twice, succeeded on the 3rd attempt - audio should
            # still end up generated and in the manifest.
            self.assertEqual(call_count["n"], 3)
            self.assertEqual(len(manifest["slides"]), 1)
            self.assertTrue((output_dir / "slide_001.mp3").exists())
            # on_retry fires once per failed attempt before the eventual
            # success (attempts 1 and 2 failed; no retry event for the
            # successful 3rd attempt).
            self.assertEqual(retry_events, [(1, 3, 1), (2, 3, 1)])

    def test_generate_audio_files_gives_up_after_max_retries(self):
        slides = [{"slide_num": 1, "title": "Intro", "notes": "Hello there"}]
        call_count = {"n": 0}

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            def always_fails_generator(text, output_path, voice):
                call_count["n"] += 1
                raise ConnectionError("network is permanently down")

            with self.assertRaises(TTSGenerationError):
                generate_audio_files(
                    slides,
                    output_dir,
                    voice="en-US-AriaNeural",
                    generator=always_fails_generator,
                    max_retries=2,
                    retry_delay_seconds=0,
                )

            # 1 initial attempt + 2 retries = 3 total attempts, then give up.
            self.assertEqual(call_count["n"], 3)

    def test_generate_audio_files_does_not_retry_missing_ffmpeg(self):
        slides = [{"slide_num": 1, "title": "Intro", "notes": "Hello there"}]
        call_count = {"n": 0}

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            def missing_ffmpeg_generator(text, output_path, voice):
                call_count["n"] += 1
                raise FileNotFoundError("ffmpeg not found")

            with self.assertRaises(TTSGenerationError):
                generate_audio_files(
                    slides,
                    output_dir,
                    voice="en-US-AriaNeural",
                    generator=missing_ffmpeg_generator,
                    retry_delay_seconds=0,
                )

            # FileNotFoundError (missing ffmpeg) is not retryable - retrying
            # wouldn't fix a missing executable, so this should fail
            # immediately on the first attempt.
            self.assertEqual(call_count["n"], 1)

    def test_generate_audio_files_retries_disabled_with_max_retries_zero(self):
        slides = [{"slide_num": 1, "title": "Intro", "notes": "Hello there"}]
        call_count = {"n": 0}

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            def always_fails_generator(text, output_path, voice):
                call_count["n"] += 1
                raise ConnectionError("network is down")

            with self.assertRaises(TTSGenerationError):
                generate_audio_files(
                    slides,
                    output_dir,
                    voice="en-US-AriaNeural",
                    generator=always_fails_generator,
                    max_retries=0,
                    retry_delay_seconds=0,
                )

            self.assertEqual(call_count["n"], 1)


    def test_generate_audio_files_does_not_retry_ssl_cert_errors(self):
        # This mirrors a real failure observed when testing against an
        # environment with a broken/self-signed certificate in the chain:
        # edge-tts (via aiohttp) raises ClientConnectorCertificateError,
        # which is-a ssl.SSLCertVerificationError. A bad certificate won't
        # become valid by retrying, so this must fail immediately.
        slides = [{"slide_num": 1, "title": "Intro", "notes": "Hello there"}]
        call_count = {"n": 0}

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            def bad_cert_generator(text, output_path, voice):
                call_count["n"] += 1
                raise ssl.SSLCertVerificationError(
                    "certificate verify failed: self-signed certificate in certificate chain"
                )

            with self.assertRaises(TTSGenerationError):
                generate_audio_files(
                    slides,
                    output_dir,
                    voice="en-US-AriaNeural",
                    generator=bad_cert_generator,
                    retry_delay_seconds=0,
                )

            self.assertEqual(call_count["n"], 1)

    def test_default_generator_writes_word_boundaries_sidecar_file(self):
        # No `generator=` override here - this exercises the real default
        # path (_default_generator_with_word_boundaries), with a fake
        # communicate_factory standing in for the network call.
        chunks = [
            {"type": "audio", "data": b"fake-mp3-bytes"},
            {"type": "WordBoundary", "text": "Hello", "offset": 0, "duration": 5_000_000},
            {"type": "WordBoundary", "text": "there", "offset": 5_000_000, "duration": 3_000_000},
        ]
        slides = [{"slide_num": 1, "title": "Intro", "notes": "Hello there"}]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            manifest = generate_audio_files(
                slides,
                output_dir,
                voice="en-US-AriaNeural",
                communicate_factory=_factory(chunks),
            )

            self.assertEqual(
                manifest["slides"][0]["word_boundaries_file"],
                "slide_001.wordboundaries.json",
            )
            sidecar_path = output_dir / "slide_001.wordboundaries.json"
            self.assertTrue(sidecar_path.exists())
            saved = json.loads(sidecar_path.read_text(encoding="utf-8"))
            self.assertEqual(
                saved,
                [
                    {"text": "Hello", "offset_seconds": 0.0, "duration_seconds": 0.5},
                    {"text": "there", "offset_seconds": 0.5, "duration_seconds": 0.3},
                ],
            )
            self.assertTrue((output_dir / "slide_001.mp3").exists())

    def test_default_generator_flags_suspected_dropped_narration(self):
        # Regression test for a real finding (see
        # subtitle_alignment.find_suspected_dropped_narration's docstring):
        # a real deck's slide 9 had edge-tts silently skip ~300 characters
        # of notes mid-slide, with no exception and no otherwise-visible
        # error. This reproduces the same shape end-to-end through
        # generate_audio_files(): a WordBoundary stream that establishes a
        # steady pace, then jumps over a large stretch of the notes text
        # with almost no time elapsed, then resumes.
        prefix = "AAAAAAAAAA"  # 10 chars, one WordBoundary each, 0.2s apart -> 5 chars/sec
        dropped = "BBBBBBBBBBBBBBBBBBBB"  # 20 chars - real notes text, but never voiced
        suffix = "CCCCCCCCCC"
        notes = prefix + dropped + suffix

        chunks = [{"type": "audio", "data": b"fake-mp3-bytes"}]
        offset_ticks = 0
        for ch in prefix:
            chunks.append({"type": "WordBoundary", "text": ch, "offset": offset_ticks, "duration": 1_600_000})
            offset_ticks += 2_000_000  # 0.2s per char
        # Jump straight to the suffix, barely any time later - the 20
        # dropped characters get none of the ~4s (20 * 0.2s) their length
        # would predict at the pace established above.
        offset_ticks += 1_000_000  # +0.1s only
        for ch in suffix:
            chunks.append({"type": "WordBoundary", "text": ch, "offset": offset_ticks, "duration": 1_600_000})
            offset_ticks += 2_000_000

        slides = [{"slide_num": 1, "title": "Intro", "notes": notes}]
        gap_calls = []

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            manifest = generate_audio_files(
                slides,
                output_dir,
                voice="en-US-AriaNeural",
                communicate_factory=_factory(chunks),
                on_narration_gap=lambda slide_num, suspect: gap_calls.append((slide_num, suspect)),
            )

            gap_warnings = manifest["slides"][0]["narration_gap_warnings"]
            self.assertEqual(len(gap_warnings), 1)
            self.assertEqual(gap_warnings[0]["skipped_text"], dropped)
            self.assertEqual(len(gap_calls), 1)
            self.assertEqual(gap_calls[0][0], 1)
            self.assertEqual(gap_calls[0][1]["skipped_text"], dropped)

    def test_custom_generator_skips_narration_gap_check(self):
        # A custom generator isn't guaranteed to produce word-boundary
        # data at all (see word_boundaries_file's own None-when-custom
        # behavior) - the narration-gap check must not run (or error) for
        # it, and narration_gap_warnings should just be an empty list.
        def custom_generator(text, output_path, voice):
            Path(output_path).write_bytes(b"fake-mp3-bytes")

        slides = [{"slide_num": 1, "title": "Intro", "notes": "Hello there"}]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            manifest = generate_audio_files(slides, output_dir, generator=custom_generator)

            self.assertEqual(manifest["slides"][0]["narration_gap_warnings"], [])

    def test_default_generator_writes_empty_sidecar_when_no_boundary_events(self):
        slides = [{"slide_num": 1, "title": "Intro", "notes": "Hello there"}]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            manifest = generate_audio_files(
                slides,
                output_dir,
                voice="en-US-AriaNeural",
                communicate_factory=_factory([{"type": "audio", "data": b"fake"}]),
            )

            self.assertEqual(
                manifest["slides"][0]["word_boundaries_file"],
                "slide_001.wordboundaries.json",
            )
            saved = json.loads((output_dir / "slide_001.wordboundaries.json").read_text(encoding="utf-8"))
            self.assertEqual(saved, [])

    def test_default_generator_word_boundaries_survive_a_retry(self):
        # The generator fails once (transient), then succeeds - the
        # word-boundary data persisted afterward should come from the
        # successful attempt, not a stale/partial one.
        call_count = {"n": 0}
        chunks = [
            {"type": "audio", "data": b"fake"},
            {"type": "WordBoundary", "text": "ok", "offset": 0, "duration": 2_000_000},
        ]

        def flaky_factory(**kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise ConnectionError("temporary network blip")
            return FakeCommunicate(chunks, **kwargs)

        slides = [{"slide_num": 1, "title": "Intro", "notes": "Hello there"}]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            manifest = generate_audio_files(
                slides,
                output_dir,
                voice="en-US-AriaNeural",
                communicate_factory=flaky_factory,
                retry_delay_seconds=0,
            )

            self.assertEqual(call_count["n"], 2)
            saved = json.loads((output_dir / "slide_001.wordboundaries.json").read_text(encoding="utf-8"))
            self.assertEqual(
                saved, [{"text": "ok", "offset_seconds": 0.0, "duration_seconds": 0.2}]
            )
            self.assertEqual(manifest["slides"][0]["word_boundaries_file"], "slide_001.wordboundaries.json")


if __name__ == "__main__":
    unittest.main()
