import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Custom React hook for speech-to-text using Web Speech API.
 * 
 * @param {Object} options
 * @param {Function} options.onResult Callback triggered when new transcription is available
 * @param {string} options.lang Language code for Speech Recognition (default: 'en-US')
 */
export default function useSpeechRecognition({ onResult, lang = 'en-US' } = {}) {
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState(null);
  const [supported, setSupported] = useState(false);
  const recognitionRef = useRef(null);

  // Store onResult in a ref so startListening doesn't recreate on callback change
  const onResultRef = useRef(onResult);
  useEffect(() => {
    onResultRef.current = onResult;
  }, [onResult]);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      setSupported(true);
    }
  }, []);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {
        console.error('Error stopping speech recognition:', e);
      }
    }
  }, []);

  const startListening = useCallback(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setError('Speech recognition is not supported in this browser. Please use a supported browser or type your question.');
      return;
    }

    // Stop and abort any existing active instance
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch (e) {
        // ignore abort errors
      }
    }

    setError(null);

    try {
      const recognition = new SpeechRecognition();
      recognitionRef.current = recognition;

      recognition.continuous = false; // Stop automatically when the user pauses/stops speaking
      recognition.interimResults = true;
      recognition.lang = lang;

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onresult = (event) => {
        let transcript = '';
        for (let i = 0; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        if (onResultRef.current) {
          onResultRef.current(transcript);
        }
      };

      recognition.onerror = (event) => {
        console.error('Speech recognition error event:', event);
        let message = 'Speech recognition error occurred.';
        
        switch (event.error) {
          case 'not-allowed':
          case 'permission-denied':
            message = 'Microphone permission denied. Please allow microphone access in your browser settings.';
            break;
          case 'no-speech':
            message = 'No speech was detected. Please try again.';
            break;
          case 'audio-capture':
            message = 'No microphone was found. Please ensure it is plugged in and configured.';
            break;
          case 'network':
            message = 'Network error occurred during speech recognition.';
            break;
          default:
            message = `Speech recognition error: ${event.error}`;
        }
        
        setError(message);
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognition.start();
    } catch (e) {
      console.error('Failed to initialize speech recognition:', e);
      setError('Failed to start speech recognition.');
      setIsListening(false);
    }
  }, [lang]);

  // Cleanup effect to abort speech recognition on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) {
          // ignore
        }
      }
    };
  }, []);

  return {
    isListening,
    error,
    supported,
    startListening,
    stopListening,
    setError
  };
}
