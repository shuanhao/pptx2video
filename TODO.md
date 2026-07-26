# TODO

## High Priority
- PowerPoint Automation
  - [x] Insert audio (`ppt_automation.py`, verified with video export)
  - [x] ~~Auto play~~ - not needed for video export (PowerPoint's "Create a
        Video" ignores the click/auto UI setting and uses the embedded
        audio's own duration/playback regardless). Still an open item if
        live Slide Show presentation mode is needed later - see
        "Known limitation" below.
  - [x] ~~Transition timing~~ - not needed; PowerPoint's video export
        automatically sizes each slide's duration to its embedded audio
        when no manual timing is recorded, so no custom logic is required.
- MP4 Export
  - [ ] Automate PowerPoint's "Create a Video" export via COM (currently a
        manual step after `--insert-audio`)

## Known Limitation (not currently planned to fix)
- Inserted audio requires a click during live Slide Show playback (editor UI
  shows "On Click"). Confirmed this does NOT affect video export. Revisit
  only if live-presentation auto-play becomes a real requirement.

## Low Priority
- Subtitle Generator (Experimental)
  - Smart segmentation
  - Reading optimization
  - Tokenizer
