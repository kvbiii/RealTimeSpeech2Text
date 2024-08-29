from fastapi import WebSocket
import websockets
import json

from transcription_utils.buffering_strategy import SilenceAtEndOfChunk

class Client:
    def __init__(
        self,
        speech2text_pipeline: object,
        vad_pipeline: object,
        sampling_rate: int = 16000,
        samples_width: int = 2,
        chunk_length_seconds: float = 3.0,
        chunk_offset_seconds: float = 0.5,
    ) -> None:
        """
        Initialize the Client object.

        Args:
            speech2text_pipeline (object): The speech-to-text pipeline.
            vad_pipeline (object): The voice activity detection pipeline.
            sampling_rate (int): The sampling rate of the audio data. It is equivalent to the number of samples per second.
            samples_width (int): The width of the audio samples in bytes. It is equivalent to the number of bytes per sample (more bytes mean higher quality).
            chunk_length_seconds (float): The length of the audio chunks in seconds. It means that the audio buffer should have at least this length to be processed.
            chunk_offset_seconds (float): The offset of the audio chunks in seconds. It means that the last chunk should end before the end of the audio buffer minus this offset to be processed.
        """
        self.speech2text_pipeline = speech2text_pipeline
        self.vad_pipeline = vad_pipeline
        self.sampling_rate = sampling_rate
        self.samples_width = samples_width
        self.buffer = bytearray()
        self.buffer_memory = bytearray()
        self.buffering_strategy = SilenceAtEndOfChunk(
            self, chunk_length_seconds, chunk_offset_seconds
        )

    async def handle_websocket(self, websocket: WebSocket) -> None:
        """
        Handle the WebSocket connection.

        Args:
            websocket (WebSocket): The WebSocket connection.
        """
        try:
            await self.handle_audio(websocket)
        except websockets.ConnectionClosed as e:
            print(f"Client disconnected: {e}")

    async def handle_audio(self, websocket: WebSocket) -> None:
        """
        Handle the audio data from the WebSocket connection.

        Args:
            websocket (WebSocket): The WebSocket connection.
        """
        try:
            while True:
                message = await websocket.receive()
                if "bytes" in message:
                    bytes_data = message["bytes"]
                    self.append_audio_data(bytes_data)
                elif "text" in message:
                    json_data = json.loads(message["text"])
                    if json_data["type"] == "stop_recording":
                        self.clear_memory()
                    elif json_data["type"] == "change_language":
                        self.send_language_change(json_data["language"])
                    else:
                        raise Exception("Unknown message type")
                else:
                    raise Exception("Unknown message type")
                self.process_audio(websocket)
        except Exception as e:
            raise Exception(f"Could not process audio: {e}")

    def append_audio_data(self, data: bytes) -> None:
        """
        Append audio data to the buffer.

        Args:
            data (bytes): The audio data to append.
        """
        self.buffer.extend(data)

    def process_audio(self, websocket: WebSocket) -> None:
        """
        Process the audio data.

        Args:
            websocket (WebSocket): The WebSocket connection.
        """
        self.buffering_strategy.process_audio(
            websocket, self.speech2text_pipeline, self.vad_pipeline
        )

    def clear_memory(self) -> None:
        """
        Clear the audio buffer memory.
        """
        self.buffer_memory.clear()
        self.buffer.clear()
        self.buffering_strategy.chunks_from_previous_segment.clear()
        self.buffering_strategy.processing_flag = False

    def send_language_change(self, language: str) -> None:
        """
        Send a language change to the speech-to-text pipeline.

        Args:
            language (str): The language to change to.
        """
        self.speech2text_pipeline.change_language(language)
