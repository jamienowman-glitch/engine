# NorthStar Engine Combos

Combos are recipes: ordered sets of engines that together deliver a higher-level ability. They describe how to stitch atomic engines into something useful.

## AUDIO.DATASET.BASIC_GRIME_V1
- **Label:** Basic grime dataset builder
- **Description:** Takes raw freestyle uploads and turns them into a LoRA-ready JSONL dataset focused on grime lyrics and flows.
- **Engines:** AUDIO.INGEST.LOCAL_V1 → AUDIO.SEGMENT.FFMPEG_V1 → AUDIO.ASR.WHISPER_V1 → TEXT.NORMALISE.SLANG_V1 → AUDIO.BEAT.FEATURES_V1 → ALIGN.AUDIO_TEXT.BARS_V1 → TAG.FLOW.AUTO_V1 → DATASET.PACK.JSONL_V1
- **Notes:** End-to-end data prep from raw files through tagging; produces train/val splits.

## TRAIN.LORA.BASIC_GRIME_V1
- **Label:** Basic grime LoRA trainer
- **Description:** Train (or currently stub-record) a LoRA using the dataset produced by AUDIO.DATASET.BASIC_GRIME_V1.
- **Engines:** DATASET.PACK.JSONL_V1 → TRAIN.LORA.LOCAL_V1
- **Notes:** Uses the placeholder trainer; swap once a real adapter trainer is available.

## AUDIO.ASR.CLEAN_PIPELINE_V1
- **Label:** Clean ASR pipeline
- **Description:** Local ingest → cleaning → segmentation → Whisper ASR → punctuation/casing for general audio.
- **Engines:** AUDIO.INGEST.LOCAL_FILE_V1 → AUDIO.PREPROCESS.BASIC_CLEAN_V1 → AUDIO.SEGMENT.FFMPEG_V1 → AUDIO.ASR.WHISPER_V1 → TEXT.CLEAN.ASR_PUNCT_CASE_V1
- **Notes:** Produces cleaner transcripts for downstream NLP or tagging.

## VIDEO.ASR.PLUS_FRAMES_V1
- **Label:** Video ASR with frame grabs
- **Description:** Ingest video, extract frames, run ASR on audio, and clean transcripts for multimodal use. Timeline/editor flows should set frame grabber to manual mode for deterministic timestamps.
- **Engines:** AUDIO.INGEST.LOCAL_FILE_V1 → VIDEO.INGEST.FRAME_GRAB_V1 → AUDIO.SEGMENT.FFMPEG_V1 → AUDIO.ASR.WHISPER_V1 → TEXT.CLEAN.ASR_PUNCT_CASE_V1
- **Notes:** Yields both text and visual context per video; manual frame grabs for editor playhead, auto mode for thumbnailing as needed.

## AUDIO.DATASET.GRIME_CLEAN_V1
- **Label:** Clean grime dataset builder
- **Description:** Remote pull ingest through cleaning, ASR, slang normalization, beat features, alignment, tagging, and JSONL packing.
- **Engines:** AUDIO.INGEST.REMOTE_PULL_V1 → AUDIO.PREPROCESS.BASIC_CLEAN_V1 → AUDIO.SEGMENT.FFMPEG_V1 → AUDIO.ASR.WHISPER_V1 → TEXT.CLEAN.ASR_PUNCT_CASE_V1 → TEXT.NORMALISE.SLANG_V1 → AUDIO.BEAT.FEATURES_V1 → ALIGN.AUDIO_TEXT.BARS_V1 → TAG.FLOW.AUTO_V1 → DATASET.PACK.JSONL_V1
- **Notes:** Higher-quality grime dataset path with cleaning + punctuation before slang-aware normalization.

## TRAIN.LORA.GRIME_CLEAN_V1
- **Label:** Grime LoRA trainer (clean path)
- **Description:** Train a LoRA adapter using the cleaned grime dataset outputs.
- **Engines:** DATASET.PACK.JSONL_V1 → TRAIN.LORA.PEFT_HF_V1
- **Notes:** Targets full PEFT/HF training instead of metadata stub.
