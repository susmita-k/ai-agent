import React, { useEffect, useRef } from 'react';
import './WebSocketClient.css';

const WebSocketClient = () => {
    // Hostname for WebSocket connections
    const hostName = "localhost";
    //const hostName = "35.208.226.141";
    // Refs for displaying messages
    const divVoiceRef = useRef(null);
    const divTranscriptRef = useRef(null);
    const divAnalysisRef = useRef(null);
    const websocketTranscriptRef = useRef(null);
    const websocketAnalysisRef = useRef(null);

    // WebSocket state & heartbeat
    let heartbeatTimeout;
    const heartbeatInterval = 10000; // 10s max between heartbeats
    let retryCount = 0;
    const maxRetries = 10;
    let websocketVoice = null;

    let audioContext;
    let mediaRecorder;

    const startAudioCapture = () => {
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then((stream) => {
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const input = audioContext.createMediaStreamSource(stream);

                // Set the sample rate to 16,000 Hz if the default is higher
                const targetSampleRate = 32000;
                const originalSampleRate = audioContext.sampleRate;
                const sampleRate = Math.min(originalSampleRate, targetSampleRate);

                mediaRecorder = new MediaRecorder(stream);

                mediaRecorder.ondataavailable = async (event) => {
                    const audioBlob = event.data;

                    // Convert audioBlob to WAV format with the target sample rate
                    const wavBlob = await convertToWav(audioBlob, sampleRate);

                    // Read the WAV blob as base64
                    const reader = new FileReader();
                    reader.onloadend = () => {
                        const base64Audio = reader.result.split(',')[1]; // Base64-encoded WAV audio
                        const payload = {
                            action: 'transcribe_translate',
                            duration: 5, // Match the 5-second interval
                            mode: 'c',
                            translate_to: 'en',
                            sample_rate: sampleRate, // Include sample rate in the payload
                            audio: base64Audio // WAV audio in base64 format
                        };
                        websocketVoice.send(JSON.stringify(payload));
                    };
                    reader.readAsDataURL(wavBlob);
                };

                mediaRecorder.start(5000); // Emit audio chunks every 5 seconds
            })
            .catch((error) => {
                console.error('Error capturing audio:', error);
            });
    };

    // Utility function to convert audioBlob to WAV format with a target sample rate
    const convertToWav = async (audioBlob, targetSampleRate) => {
        const arrayBuffer = await audioBlob.arrayBuffer();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

        // Resample the audio if the target sample rate is lower than the original
        const resampledBuffer = targetSampleRate < audioBuffer.sampleRate
            ? await resampleAudioBuffer(audioBuffer, targetSampleRate)
            : audioBuffer;

        // Force mono channel by averaging all channels
        const numChannels = 1; // Set to mono
        const length = resampledBuffer.length * numChannels * 2 + 44; // WAV header + PCM data
        const wavBuffer = new ArrayBuffer(length);
        const view = new DataView(wavBuffer);

        // Write WAV header
        writeWavHeader(view, resampledBuffer, targetSampleRate, numChannels);

        // Write PCM data
        let offset = 44;
        const channelData = resampledBuffer.getChannelData(0); // Use the first channel
        for (let i = 0; i < channelData.length; i++) {
            const sample = Math.max(-1, Math.min(1, channelData[i])); // Clamp to [-1, 1]
            view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true); // PCM 16-bit
            offset += 2; // 2 bytes per sample (16-bit)
        }

        return new Blob([view], { type: 'audio/wav' });
    };

    // Utility function to resample an AudioBuffer
    const resampleAudioBuffer = async (audioBuffer, targetSampleRate) => {
        const offlineContext = new OfflineAudioContext(
            1, // Mono channel
            Math.ceil(audioBuffer.duration * targetSampleRate),
            targetSampleRate
        );
        const source = offlineContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(offlineContext.destination);
        source.start(0);
        return await offlineContext.startRendering();
    };

    // Utility function to write WAV header
    const writeWavHeader = (view, audioBuffer, sampleRate, numChannels) => {
        const sampleRateInBytes = sampleRate * numChannels * 2; // Byte rate
        const dataSize = audioBuffer.length * numChannels * 2; // PCM data size

        // RIFF chunk descriptor
        writeString(view, 0, 'RIFF');
        view.setUint32(4, 36 + dataSize, true); // File size - 8 bytes
        writeString(view, 8, 'WAVE');

        // fmt sub-chunk
        writeString(view, 12, 'fmt ');
        view.setUint32(16, 16, true); // Sub-chunk size (16 for PCM)
        view.setUint16(20, 1, true); // Audio format (1 for PCM)
        view.setUint16(22, numChannels, true); // Number of channels (1 for mono)
        view.setUint32(24, sampleRate, true); // Sample rate
        view.setUint32(28, sampleRateInBytes, true); // Byte rate
        view.setUint16(32, numChannels * 2, true); // Block align (numChannels * bytes per sample)
        view.setUint16(34, 16, true); // Bits per sample (16 bits)

        // data sub-chunk
        writeString(view, 36, 'data');
        view.setUint32(40, dataSize, true); // Data size
    };

    // Utility function to write strings to DataView
    const writeString = (view, offset, string) => {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    };

    // Utility to append a message to a div
    const appendToDiv = (divRef, text) => {
        const p = document.createElement('p');
        p.textContent = text;
        divRef.current.appendChild(p);
        divRef.current.scrollTop = divRef.current.scrollHeight;
    };

    // Reset heartbeat timeout when a heartbeat is received
    const resetHeartbeatTimeout = () => {
        clearTimeout(heartbeatTimeout);
        heartbeatTimeout = setTimeout(() => {
            console.warn("voice: No heartbeat recd in time. Reconnecting...");
            websocketVoice?.close(); // force reconnect
        }, heartbeatInterval);
    };

    // Attempt to reconnect with exponential-ish backoff
    const attemptReconnect = () => {
        if (retryCount >= maxRetries) {
            console.error("voice: Reconn: max retries reached.");
            return;
        }
        retryCount++;
        setTimeout(() => {
            console.log(`voice: Reconn (#${retryCount})...`);
            connectVoiceWebSocket();
        }, 3000);
    };

    // Setup the Voice WebSocket connection
    const connectVoiceWebSocket = () => {
        websocketVoice = new WebSocket(`ws://${hostName}:8081/ws`);
        websocketVoice.onopen = () => {
            console.log('voice: Connected');
            appendToDiv(divVoiceRef, 'Connected');

            // Reset retries on successful connection
            retryCount = 0;

            // Start heartbeat timeout tracking
            resetHeartbeatTimeout();

            // Start audio capture
            startAudioCapture();
        };

        websocketVoice.onmessage = (event) => {
            //console.log("***HERE websocketVoice***", event);
            try {
                // Handle heartbeat separately
                if (event && event.data === "heartbeat") {
                    console.log('voice: heartbeat');
                    resetHeartbeatTimeout();
                    return;
                }

                // Normal message handling
                const message = JSON.parse(event.data);
                //console.log('Received from Voice WebSocket:[', message, ']');
                if (message !== "heartbeat") {
                    let strMsg = JSON.stringify(message, null, 2);
                    appendToDiv(divVoiceRef, `Recd: ${strMsg}`);
                }
            } catch (e) {
                console.error('voice: Error parsing message:', e);
            }
        };

        websocketVoice.onclose = () => {
            console.warn('voice: closed');
            appendToDiv(divVoiceRef,  `Disconnected: ${event.code}, ${event.reason}`);
            clearTimeout(heartbeatTimeout);
            attemptReconnect();
        };

        websocketVoice.onerror = (error) => {
            console.error('voice: error:', error);
            appendToDiv(divVoiceRef, `Error: ${error}, ${event.code}, ${event.reason}`);
            websocketVoice.close();
        };
    }; // end of connectVoiceWebSocket

    // Attempt to reconnect Transcript WebSocket
    const attemptReconnectTranscript = () => {
        console.log('transcribe: reconn attempt');
        if (retryCount >= maxRetries) {
            console.error("transcribe: reconn attempt: max retries reached");
            return;
        }
        retryCount++;
        setTimeout(() => {
            console.log(`transcript: reconn attempt (#${retryCount})...`);
            connectTranscriptWebSocket();
        }, 3000);
    };

    // Attempt to reconnect Analysis WebSocket
    const attemptReconnectAnalysis = () => {
        console.log('analysis: reconn attempt');
        if (retryCount >= maxRetries) {
            console.error("analysis: reconn attempt: max retries reached");
            return;
        }
        retryCount++;
        setTimeout(() => {
            console.log(`analysis: reconn attempt (#${retryCount})...`);
            connectAnalysisWebSocket();
        }, 3000);
    };

    // Setup the Transcript WebSocket connection
    const connectTranscriptWebSocket = () => {
        websocketTranscriptRef.current = new WebSocket(`ws://${hostName}:6081/ws`);
        const websocketTranscript = websocketTranscriptRef.current;
        //let websocketTranscript = new WebSocket(`ws://${hostName}:6081/ws`);
        websocketTranscript.onopen = () => appendToDiv(divTranscriptRef, 'Connected');
        websocketTranscript.onmessage = (event) => {
            console.log("[DBG]useEffect -> [websocketTranscript] event:", event);
            if (event.data !== "heartbeat") {
                try {
                    const message = JSON.parse(event.data);
                    let strMsg = JSON.stringify(message, null, 2);
                    appendToDiv(divTranscriptRef, `Received: ${JSON.parse(strMsg).translation_output}`);
                } catch (error) {
                    console.error("transcript: Error parsing msg:", error);
                }
            } else {
                console.log('[DBG]useEffect -> [websocketTranscript]transcript:heartbeat');
            }
        };
        websocketTranscript.onclose = () => {
            console.warn('transcript: closed');
            appendToDiv(divTranscriptRef, `Disconnected: ${event.code}, ${event.reason}`);
            attemptReconnectTranscript();
        };
        websocketTranscript.onerror = (error) => {
            console.error('transcript: error:', error);
            appendToDiv(divTranscriptRef, `Error: ${error}`);
            websocketTranscript.close();
        };
    };

    // Setup the Analysis WebSocket connection
    const connectAnalysisWebSocket = () => {
        websocketAnalysisRef.current = new WebSocket(`ws://${hostName}:7081/ws`);
        const websocketAnalysis = websocketAnalysisRef.current;    
        //let websocketAnalysis = new WebSocket(`ws://${hostName}:7081/ws`);
        websocketAnalysis.onopen = () => appendToDiv(divAnalysisRef, 'Connected');
        websocketAnalysis.onmessage = (event) => {
            try {
                console.log("[DBG]useEffect -> [websocketAnalysis] modelresp, event:", event);
                if (event.data !== "heartbeat") {
                    const message = JSON.parse(event.data);
                    console.log('[DBG]useEffect ->Recd from Analysis ws:', message.diagnosis_summary);
                    appendToDiv(divAnalysisRef, `Diagnosis summary: ${message.diagnosis_summary}`);
                } else {
                    console.log('modelresp: heartbeat');
                }
            } catch (e) {
                console.error('analysis: Error parsing msg:', e);
            }
        };
        websocketAnalysis.onclose = () => {
            console.warn('analysis: closed');
            appendToDiv(divAnalysisRef, `Disconnected: ${event.code}, ${event.reason}`);
            attemptReconnectAnalysis();
        };
        websocketAnalysis.onerror = (error) => {
            console.error('analysis: error:', error);
            appendToDiv(divAnalysisRef, `Error: ${error}`);
            websocketAnalysis.close();
        };
    };

    // Main effect to initialize and manage all sockets
    useEffect(() => {
        console.log('[DBG]useEffect -> WS mounted');
        connectVoiceWebSocket();
        connectTranscriptWebSocket();
        connectAnalysisWebSocket();

        // Periodically check WebSocket connections
        const checkWebSocketConnections = setInterval(() => {
            // Check Voice WebSocket
            if (websocketVoice?.readyState !== WebSocket.OPEN) {
                console.warn('voice: not connected. Attempting reconn');
                try {
                    connectVoiceWebSocket();
                } catch (error) {
                    console.error('voice: reconnect failed:', error);
                }
            }

            // Check Transcript WebSocket
            if (websocketTranscriptRef.current?.readyState !== WebSocket.OPEN) {
                console.warn('transcript: not connected. Attempting reconn');
                try {
                    connectTranscriptWebSocket();
                } catch (error) {
                    console.error('transcript: reconnect failed:', error);
                }
            }

            // Check Analysis WebSocket
            if (websocketAnalysisRef.current?.readyState !== WebSocket.OPEN) {
                console.warn('analysis: not connected. Attempting reconn');
                try {
                    connectAnalysisWebSocket();
                } catch (error) {
                    console.error('analysis: reconnect failed:', error);
                }
            }
        }, 10000); // Check every 10 seconds

        // Clean up on unmount
        return () => {
            websocketVoice?.close();
            websocketTranscriptRef.current?.close();
            websocketAnalysisRef.current?.close();
            // websocketTranscript.close();
            // websocketAnalysis.close();if (websocketTranscriptRef.current?.readyState !== WebSocket.OPEN) {
            //if (websocketTranscriptRef.current?.readyState !== WebSocket.OPEN) {
                clearTimeout(heartbeatTimeout);
                clearInterval(checkWebSocketConnections);
            //}
        };
    }, []);

    // JSX for rendering the UI
    return (
        <div className="container">
            <div>
                <h3>Voice:</h3>
                <div ref={divVoiceRef} className="scrollable-div"></div>
            </div>
            <div>
                <h3>Transcript:</h3>
                <div ref={divTranscriptRef} className="scrollable-div"></div>
            </div>
            <div>
                <h3>Model Query:</h3>
                <div ref={divAnalysisRef} className="scrollable-div"></div>
            </div>
        </div>
    );
};

export default WebSocketClient;
