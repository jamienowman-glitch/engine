# NorthStar Engine Registry

This registry tracks atomic engines for the NorthStar OS. Engines are reusable building blocks that can be assembled into higher-level abilities. Bot Better Know is the first source lab contributing parts here.

## Source Labs
- Bot Better Know — `engines/bot-better-know/pipeline/` — grime/audio dataset lab.

## Engine Table
| Engine ID | Label | Category | Source pipeline(s) | Primary script | Inputs | Outputs | OSS deps |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AUDIO.INGEST.LOCAL_V1 | Local/GCS inbox sync runner | ingest | bot-better-know | engines/bot-better-know/pipeline/ingest.py | GCS inbox bucket or local upload dir | Local working dirs with inbox/segments/asr/aligned/datasets/model populated | gsutil, python |
| AUDIO.SEGMENT.FFMPEG_V1 | FFmpeg audio segmenter | audio | bot-better-know | engines/bot-better-know/pipeline/01_segment_ffmpeg.py | Raw audio/video file | Mono mp3 segments (~90s) | ffmpeg |
| AUDIO.ASR.WHISPER_V1 | Whisper ASR (faster-whisper) | asr | bot-better-know | engines/bot-better-know/pipeline/02_whisper_asr.py | Segmented mp3 audio | Whisper JSON with segments + word timings | faster-whisper, ctranslate2 |
| TEXT.NORMALISE.SLANG_V1 | Slang-preserving normalizer | text | bot-better-know | engines/bot-better-know/pipeline/02b_normalize_slang.py | Whisper JSON payload | Normalized JSON (.norm) with slang-aware tokens | python |
| AUDIO.BEAT.FEATURES_V1 | Beat/tempo analyzer | audio-analysis | bot-better-know | engines/bot-better-know/pipeline/03_beat_features.py | Segmented mp3 audio | Meta JSON with bpm, downbeats, 16th grid | librosa |
| ALIGN.AUDIO_TEXT.BARS_V1 | Word-to-bar aligner | alignment | bot-better-know | engines/bot-better-know/pipeline/04_align_words.py | ASR JSON (+ beat metadata) | Bar JSON with text, syllables, stress slots | python |
| TAG.FLOW.AUTO_V1 | Rule-based flow tagger | tagging | bot-better-know | engines/bot-better-know/pipeline/05_auto_tag_flow.py | Bar JSON | Bar JSON + CSV with flow predictions | python |
| DATASET.PACK.JSONL_V1 | Bars to JSONL packer | dataset | bot-better-know | engines/bot-better-know/pipeline/06_pack_jsonl.py | Bar JSON (+ optional flow CSV) | train.jsonl and val.jsonl files | python |
| TRAIN.LORA.LOCAL_V1 | LoRA metadata trainer placeholder | training | bot-better-know | engines/bot-better-know/pipeline/07_train_lora.py | train.jsonl and val.jsonl | adapter_config.json metadata stub | python |

## New Atomic Engines (registry-only specs)
- **AUDIO.PREPROCESS.BASIC_CLEAN_V1** — Basic noise/level/pops cleanup before ASR.  
  - Inputs: raw mono/stereo audio.  
  - Outputs: cleaned/stabilized audio suitable for segmentation/ASR.  
  - Tech: ffmpeg/sox-style filters (denoise, normalize).
- **VIDEO.INGEST.FRAME_GRAB_V1** — Grab representative frames from video uploads.  
  - Inputs (auto mode): video_uri, frame_every_n_seconds, optional max_frames.  
  - Inputs (manual mode): video_uri, timestamps_ms[].  
  - Outputs: still frames (jpg/png) plus {timestamp_ms, frame_uri} list and basic meta.  
  - Tech: ffmpeg frame extraction; manual mode is timeline-driven (no heuristic frame picking).
- **TEXT.CLEAN.ASR_PUNCT_CASE_V1** — Restore punctuation and casing to ASR text.  
  - Inputs: raw ASR transcript JSON/text.  
  - Outputs: punctuated/cased transcript JSON/text.  
  - Tech: lightweight NLP/regex detokenization.
- **AUDIO.INGEST.LOCAL_FILE_V1** — Stage local audio/video files into a working inbox.  
  - Inputs: local path(s) to user-provided media.  
  - Outputs: organized staging directory for downstream engines.  
  - Tech: filesystem copy/move, format validation.
- **AUDIO.INGEST.REMOTE_PULL_V1** — Pull remote audio/video to local staging.  
  - Inputs: remote URL or bucket/object reference.  
  - Outputs: staged media files ready for preprocessing/segmentation.  
  - Tech: curl/wget/gsutil-style fetch.
- **TRAIN.LORA.PEFT_HF_V1** — Actual LoRA fine-tuning via PEFT/HuggingFace.  
  - Inputs: train/val JSONL dataset paths, base model ref, config.  
  - Outputs: LoRA adapter weights/artifacts and training metrics.  
  - Tech: PyTorch + HuggingFace PEFT/transformers.

## Future Engines / Wishlist
- VIDEO.FRAME.GRAB_V1 — extract frame stills/thumbnails from uploads.
- AUDIO.DENOISE.BASIC_V1 — clean noisy mic recordings before ASR.
- TEXT.CLEAN.PUNCTUATION_V1 — restore punctuation/capitalization post-ASR.
- TRAIN.LORA.FULL_FT_V1 — actual LoRA fine-tuning pipeline (beyond metadata stub).
