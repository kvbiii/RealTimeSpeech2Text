import os
import wave
import torch
from silero_vad import save_audio


async def save_buffer_to_file(data: bytearray) -> str:
    """
    Save the audio data to a file.

    Args:
        data (bytearray): The audio data to save.

    Returns:
        str: The path to the saved file.
    """
    os.makedirs("audio_files", exist_ok=True)
    file_path = os.path.join("audio_files", "output.wav")
    with wave.open(file_path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(data)
    return file_path


async def save_chunks_to_file(chunks: torch.Tensor) -> None:
    """
    Save the audio chunks to a file.

    Args:
        chunks (torch.Tensor): The audio chunks to save.
    """
    save_audio(f"audio_files/chunks.wav", chunks, sampling_rate=16000)
