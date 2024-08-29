let websocket;
let context;
let processor;
let globalStream;
let isRecording = false;

const websocket_address = document.querySelector('#websocket_address');
const websocket_status = document.querySelector('#websocket_status');
const websocket_connect_button = document.querySelector("#websocket_connect_button");
const language_selection = document.querySelector('.language-selection');
const selected_language = document.querySelector('#language');
const start_recording_button = document.querySelector('#start_recording_button');
const stop_recording_button = document.querySelector('#stop_recording_button');
const transcription_block = document.querySelector('#transcription_block');
const processing_time = document.querySelector('#processing_time');
const recording_gif = document.querySelector('.recording-gif');

websocket_address.addEventListener("input", resetWebsocketHandler);
websocket_address.addEventListener("keydown", (event) => {
    if (event.key === 'Enter') {
        event.preventDefault();
        connectWebsocketHandler();
    }
});
websocket_connect_button.addEventListener("click", connectWebsocketHandler);


function resetWebsocketHandler() {
    if (isRecording) {
        stopRecordingHandler();
    }
    if (websocket.readyState === WebSocket.OPEN) {
        websocket.close();
    }
    websocket_connect_button.disabled = false;
}

function connectWebsocketHandler() {
    if (!websocket_address.value) {
        console.log("WebSocket address is required.");
        return;
    }

    websocket = new WebSocket(websocket_address.value);
    websocket.onopen = () => {
        setTimeout(() => {
            websocket_status.textContent = '✅ Connected';
            language_selection.classList.remove('hidden');
            selected_language.disabled = false;
            selected_language.value = 'pl'; // Automatically select Polish
            start_recording_button.disabled = false;
            websocket_connect_button.disabled = true;
            sendLanguageChange(selected_language.value);
            console.log("WebSocket connection established");
        }, 200);
    };
    websocket.onclose = event => {
        console.log("WebSocket connection closed", event);
        websocket_status.textContent = '❌ Not Connected';
        start_recording_button.disabled = true;
        stop_recording_button.disabled = true;
        websocket_connect_button.disabled = false;
    };
    websocket.onmessage = event => {
        console.log("Message from server:", event.data);
        const transcript_data = JSON.parse(event.data);
        updateTranscription(transcript_data);
    };
    websocket.onerror = event => {
        console.log("WebSocket error", error);
        websocket_status.textContent = '❌ Error';
        start_recording_button.disabled = true;
        stop_recording_button.disabled = true;
    };
}

selected_language.addEventListener("change", (event) => {
    sendLanguageChange(event.target.value);
});

function sendLanguageChange(language) {
    if (websocket && websocket.readyState === WebSocket.OPEN && isRecording === false) {
        websocket.send(JSON.stringify({type: 'change_language', language: language}));
        console.log("Language changed to", language);
    }
}

function updateTranscription(transcript_data) {
    if (Array.isArray(transcript_data.words) && transcript_data.words.length > 0) {
        // Append words with color based on their probability
        transcript_data.words.forEach(wordData => {
            const span = document.createElement('span');
            const probability = wordData.probability;
            span.textContent = wordData.word + ' ';
            span.style.color = calculateColor(probability);

            transcription_block.appendChild(span);
        });

        // Add a new line at the end
        transcription_block.appendChild(document.createElement('br'));
    } else {
        // Fallback to plain text
        const span = document.createElement('span');
        span.textContent = transcript_data.text;
        transcription_block.appendChild(span);
        transcription_block.appendChild(document.createElement('br'));
    }

    // Update the processing time, if available
    if (transcript_data.processing_time) {
        processing_time.textContent = 'Processing time: ' + transcript_data.processing_time.toFixed(2) + ' seconds';
    }
}

function calculateColor(probability) {
    let red, green, blue = 0;

    if (probability < 0.3) {
        // Darker red for lower probabilities
        red = 180;
        green = Math.floor(255 * probability / 0.3);
    } else if (probability < 0.6) {
        // Yellow to red gradient
        red = 180;
        green = Math.floor(255 * (1 - (probability - 0.3) / 0.3));
    } else {
        // Green gradient
        red = Math.floor(255 * (1 - probability+0.15));
        green = 180;
    }

    return `rgb(${red}, ${green}, ${blue})`;
}

start_recording_button.addEventListener("click", startRecordingHandler);

function startRecordingHandler() {
    if (isRecording) return;
    isRecording = true;

    context = new AudioContext();

    let onSuccess = async (stream) => {
        globalStream = stream;
        const input = context.createMediaStreamSource(stream);
        start_recording_button.disabled = true;
        stop_recording_button.disabled = false;
        selected_language.disabled = true;
        recording_gif.removeAttribute('hidden');
        console.log("Recording started");
        const recordingNode = await setupRecordingWorkletNode();
        // Disable start button and enable stop button
        recordingNode.port.onmessage = (event) => {
            processAudio(event.data);
        };
        input.connect(recordingNode);
    };
    let onError = (error) => {
        console.error(error);
    };
    navigator.mediaDevices.getUserMedia({
        audio: {
            echoCancellation: true,
            autoGainControl: false,
            noiseSuppression: true,
            latency: 0
        }
    }).then(onSuccess, onError);
}

async function setupRecordingWorkletNode() {
    await context.audioWorklet.addModule('app/static/realtime-audio-processor.js');

    return new AudioWorkletNode(
        context,
        'realtime-audio-processor'
    );
}

stop_recording_button.addEventListener("click", stopRecordingHandler);

function stopRecordingHandler() {
    if (!isRecording) return;
    isRecording = false;

    if (globalStream) {
        globalStream.getTracks().forEach(track => track.stop());
    }
    if (processor) {
        processor.disconnect();
        processor = null;
    }
    if (context) {
        context.close().then(() => context = null);
    }
    start_recording_button.disabled = false;
    stop_recording_button.disabled = true;
    selected_language.disabled = false;
    recording_gif.setAttribute('hidden', 'true');
    console.log("Recording stopped");
    websocket.send(JSON.stringify({type: 'stop_recording'}));
}

function processAudio(sampleData) {
    const outputSampleRate = 16000;
    const decreaseResultBuffer = decreaseSampleRate(sampleData, context.sampleRate, outputSampleRate);
    const audioData = convertFloat32ToInt16(decreaseResultBuffer);

    if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(audioData);
    }
}

function decreaseSampleRate(buffer, inputSampleRate, outputSampleRate) {
    if (inputSampleRate < outputSampleRate) {
        console.error("Sample rate too small.");
        return;
    } else if (inputSampleRate === outputSampleRate) {
        return;
    }

    let sampleRateRatio = inputSampleRate / outputSampleRate;
    let newLength = Math.ceil(buffer.length / sampleRateRatio);
    let result = new Float32Array(newLength);
    let offsetResult = 0;
    let offsetBuffer = 0;
    while (offsetResult < result.length) {
        let nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
        let accum = 0, count = 0;
        for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
            accum += buffer[i];
            count++;
        }
        result[offsetResult] = accum / count;
        offsetResult++;
        offsetBuffer = nextOffsetBuffer;
    }
    return result;
}

function convertFloat32ToInt16(buffer) {
    let l = buffer.length;
    const buf = new Int16Array(l);
    while (l--) {
        buf[l] = Math.min(1, buffer[l]) * 0x7FFF;
    }
    return buf.buffer;
}
