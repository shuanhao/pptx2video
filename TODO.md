# TODO

## High Priority
- PowerPoint Automation
  - [x] Insert audio (`ppt_automation.py: insert_audio`, verified with video export)
  - [x] ~~Auto play~~ - not needed for video export (PowerPoint's "Create a
        Video" ignores the click/auto UI setting and uses the embedded
        audio's own duration/playback regardless). Still an open item if
        live Slide Show presentation mode is needed later - see
        "Known limitation" below.
  - [x] ~~Transition timing~~ - not needed; PowerPoint's video export
        automatically sizes each slide's duration to its embedded audio
        when no manual timing is recorded, so no custom logic is required.
- MP4 Export
  - [x] Automate PowerPoint's "Create a Video" export via COM
        (`ppt_automation.py: export_video`). Verified end-to-end on real
        Windows + PowerPoint: video plays correctly, per-slide duration
        matches audio length.

## Nice to Have
- [ ] Progress reporting for `--insert-audio` (`--generate-audio` and
      `--export-video` already report progress in real time; the audio
      insertion loop doesn't yet)

## Known Limitation (not currently planned to fix)
- Inserted audio requires a click during live Slide Show playback (editor UI
  shows "On Click"). Confirmed this does NOT affect video export. Revisit
  only if live-presentation auto-play becomes a real requirement.
- `CreateVideoStatus`'s enum values are taken from Microsoft's documented
  `PpMediaTaskStatus` reference, not individually verified against every
  PowerPoint COM version. A safety-net check (confirms the output file
  exists and is non-empty after a reported "done" status) mitigates this.

## Low Priority
- Subtitle Generator (Experimental)
  - Smart segmentation
  - Reading optimization
  - Tokenizer
  - Integrate into the main pipeline (currently a standalone PoC)
