# Real Time Speech Recognition Application

## Overview

Welcome to the Real Time Speech Recognition Application! 

This application is designed to transcribe speech in real-time using:
- **FastAPI**: web framework for building APIs.
- **WebSockets**: communication protocol.
- **Faster Whisper**: speech recognition model.
- **Silero VAD**: voice activity detection model.

## Installation

To get started with the Speech Recognition Application, follow these steps:

1. **Clone the Repository**:
    ```sh
    git clone https://github.com/yourusername/Speech_recognition.git
    cd Speech_recognition
    ```

2. **Install Dependencies**:
    ```sh
    pip install -r requirements.txt
    ```

3. **Set Up Environment Variables**:
    After installing all dependencies, run the following command in your terminal to set up the necessary environment variables:
    ```sh
    export LD_LIBRARY_PATH=`python3 -c 'import os; import nvidia.cublas.lib; import nvidia.cudnn.lib; import torch; print(os.path.dirname(nvidia.cublas.lib.__file__) + ":" + os.path.dirname(nvidia.cudnn.lib.__file__) + ":" + os.path.dirname(torch.__file__) +"/lib")'`
    ```

## Usage

To run the application, execute the following command:
```sh
fastapi dev
```