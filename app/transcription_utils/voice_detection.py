from typing import List, Tuple
import numpy as np
from silero_vad import load_silero_vad, read_audio, get_speech_timestamps

from transcription_utils.audio_utils import save_buffer_to_file


class VoiceActivityDetectionPipeline:
    def __init__(self) -> None:
        """
        Initialize the VoiceActivityDetectionPipeline object.
        """
        self.model = load_silero_vad()

    async def detect_activity(
        self, client: object
    ) -> Tuple[np.ndarray, List[Tuple[float, float]]]:
        """
        Detect voice activity in the audio buffer.

        Args:
            client (object): The client object.

        Returns:
            Tuple[np.ndarray, List[Tuple[float, float]]]: The audio data and the speech segments.
        """
        file_path = await save_buffer_to_file(client.buffer_memory)
        wav = read_audio(file_path)
        speech_segments = get_speech_timestamps(
            wav, self.model, sampling_rate=client.sampling_rate
        )
        return wav, speech_segments
