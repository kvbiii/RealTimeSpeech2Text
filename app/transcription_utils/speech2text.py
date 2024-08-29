import os
import torch
from faster_whisper import WhisperModel
from typing import Dict, Any


class Speech2TextPipeline:
    def __init__(self) -> None:
        """
        Initialize the Speech2TextPipeline object.
        """
        device = "cuda" if torch.cuda.is_available() else "cpu"
        torch_dtype = "float16" if torch.cuda.is_available() else "float32"
        model_size = "medium"
        self.pipe = WhisperModel(model_size, device=device, compute_type=torch_dtype)
        self.file_path = "audio_files/chunks.wav"

    async def transcribe(self) -> Dict[str, Any]:
        """
        Transcribe the audio file using faster-whisper.

        Returns:
            Dict[str, Any]: The transcription of the audio file.
        """
        if os.path.exists(self.file_path) == False:
            return {"text": "", "words": []}
        segments, _ = self.pipe.transcribe(
            self.file_path, language=self.language, word_timestamps=True
        )
        os.remove(self.file_path)
        segments = list(segments)
        flattened_words = [word for segment in segments for word in segment.words]
        return {
            "text": " ".join([word.word for word in flattened_words]),
            "words": [
                {
                    "word": word.word,
                    "probability": word.probability,
                    "start_time": word.start,
                    "end_time": word.end,
                }
                for word in flattened_words
            ],
        }

    def change_language(self, language: str) -> None:
        """
        Change the language of the speech-to-text pipeline.

        Args:
            language (str): The language to change to.
        """
        self.language = language
