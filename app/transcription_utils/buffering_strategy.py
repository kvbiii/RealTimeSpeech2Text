import asyncio
from timeit import default_timer as timer
import torch
from fastapi import WebSocket
from typing import List, Dict

from transcription_utils.audio_utils import save_chunks_to_file


class SilenceAtEndOfChunk:
    def __init__(
        self, client: object, chunk_length_seconds: float, chunk_offset_seconds: float
    ) -> None:
        """
        Initialize the SilenceAtEndOfChunk buffering strategy.

        Args:
            client (object): The client object.
            chunk_length_seconds (float): The length of the audio chunks in seconds. It means that the audio buffer should have at least this length to be processed.
            chunk_offset_seconds (float): The offset of the audio chunks in seconds. It means that the last chunk should end before the end of the audio buffer minus this offset to be processed.
        """
        self.chunks_from_previous_segment = []
        self.client = client
        self.chunk_length_seconds = chunk_length_seconds
        self.chunk_offset_seconds = chunk_offset_seconds
        self.chunk_length_in_bytes = (
            self.chunk_length_seconds
            * self.client.sampling_rate
            * self.client.samples_width
        )
        self.last_segment_should_end_before = (
            self.chunk_length_seconds - self.chunk_offset_seconds
        ) * self.client.sampling_rate
        self.segment_should_start_after = (
            self.chunk_offset_seconds * self.client.sampling_rate
        )
        self.processing_flag = False

    def process_audio(
        self,
        websocket: WebSocket,
        speech2text_pipeline: object,
        vad_pipeline: object,
    ) -> None:
        """
        Process audio for activity detection and transcription.

        Args:
            websocket (WebSocket): The WebSocket connection for sending transcriptions.
            speech2text_pipeline (object): The automatic speech recognition pipeline.
            vad_pipeline (object): The voice activity detection pipeline.
        """
        if len(self.client.buffer) > self.chunk_length_in_bytes:
            if self.processing_flag:
                raise Exception(
                    "Error in realtime processing: tried processing a new chunk while the previous one was still being processed"
                )
            self.client.buffer_memory += self.client.buffer
            self.client.buffer.clear()
            self.processing_flag = True
            asyncio.create_task(
                self.process_audio_async(websocket, speech2text_pipeline, vad_pipeline)
            )

    async def process_audio_async(
        self,
        websocket: WebSocket,
        speech2text_pipeline: object,
        vad_pipeline: object,
    ) -> None:
        """
        Asynchronously process audio for activity detection and transcription.

        Args:
            websocket (WebSocket): The WebSocket connection for sending transcriptions.
            speech2text_pipeline (object): The automatic speech recognition pipeline.
            vad_pipeline (object): The voice activity detection pipeline
        """
        start = timer()
        wav, speech_segments = await vad_pipeline.detect_activity(self.client)
        if len(speech_segments) == 0:
            self.client.buffer_memory.clear()
            if len(self.chunks_from_previous_segment) == 0:
                self.processing_flag = False
                return
        await self.buffering_strategy_save_chunks(wav, speech_segments)
        transcription = await speech2text_pipeline.transcribe()
        if transcription["text"] != "":
            transcription["processing_time"] = timer() - start
            await websocket.send_json(transcription)
        self.client.buffer_memory.clear()
        self.processing_flag = False

    async def buffering_strategy_save_chunks(
        self, wav: torch.Tensor, speech_segments: List[Dict[str, int]]
    ) -> None:
        """
        Save the audio chunks to a file.

        Args:
            wav (torch.Tensor): The audio tensor.
            speech_segments (List[Dict[str, int]]): The speech segments.
        """
        if len(speech_segments) == 0:
            await save_chunks_to_file(torch.cat(self.chunks_from_previous_segment))
            self.chunks_from_previous_segment = []
            return
        last_segment_end = speech_segments[-1]["end"]
        if last_segment_end < self.last_segment_should_end_before:
            await self.save_chunks(wav, speech_segments)
        else:
            if len(speech_segments) > 1:
                await self.save_chunks(wav, speech_segments[:-1])
            elif (
                len(self.chunks_from_previous_segment) > 0
                and speech_segments[0]["start"] > self.segment_should_start_after
            ):
                await save_chunks_to_file(torch.cat(self.chunks_from_previous_segment))
                self.chunks_from_previous_segment = []
            self.chunks_from_previous_segment.append(
                wav[speech_segments[-1]["start"] :]
            )

    async def save_chunks(
        self, wav: torch.Tensor, speech_segments: List[Dict[str, int]]
    ) -> None:
        """
        Save the audio chunks to a file.

        Args:
            wav (torch.Tensor): The audio tensor.
            speech_segments (List[Dict[str, int]]): The speech segments.
        """
        chunks = self.chunks_from_previous_segment
        for segment in speech_segments:
            chunks.append(wav[segment["start"] : segment["end"]])
        self.chunks_from_previous_segment = []
        chunks_to_save = torch.cat(chunks)
        await save_chunks_to_file(chunks_to_save)
