You are captioning frames from a video. CONTEXT: {context}

Read {batch_file}. It lists frames. Each has an id, a video timestamp, an image path, and the
speech (Whisper transcript) that started while that frame was on screen.

For EVERY frame, in order: use the Read tool on its image path, then write its caption. Open each
image by its exact path; never caption a frame you have not opened, and never infer one from a
neighbour.

Caption format, one block per frame:
### <id> @ <timestamp>
- File: <image filename, e.g. f_00233.jpg>
- Screen: what is shown (app screen/dialog, slide, scene, person, setting).
- Visible text: transcribe the important on-screen text exactly: form field labels AND values,
  headings, column headers, buttons, dialog titles, warnings/toasts, names, numbers, code. List every
  form field label you can read. Write "unreadable" rather than guessing.
- Action/change: what is happening or changed since the previous frame. Say "loading/transitional"
  for mid-load frames.
- Speech: one-line gist of the speech for this frame, or "none".
- Screen vs speech: anything said that is NOT shown, shown but not said, or that conflicts
  (e.g. a name spelled differently on screen than the transcript).

Report only what is in the image or the given speech. Mark uncertain readings "(?)".
{focus}
Write all captions with the Write tool to {captions_file}, then reply only "done N frames".
