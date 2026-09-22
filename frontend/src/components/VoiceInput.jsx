import React, { useEffect, useRef, useState } from 'react';

export default function VoiceInput({ onTranscript }) {
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState('');

  const recognitionRef = useRef(null);

  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setError('Voice input is not supported in this browser.');
      return;
    }

    const recognition = new SpeechRecognition();

    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setIsListening(true);
      setError('');
    };

    recognition.onresult = (event) => {
      let transcript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }

      onTranscript(transcript);
    };

    recognition.onerror = (event) => {
      setIsListening(false);

      console.log('Speech Recognition Error:', event.error);

      if (event.error === 'not-allowed') {
        setError('Microphone permission was denied.');
      } else if (event.error === 'no-speech') {
        setError('No speech detected. Please try again.');
      } else {
        setError(`Voice input error: ${event.error}`);
      }
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;

    return () => {
      recognition.stop();
    };
  }, [onTranscript]);

  const toggleListening = () => {
    if (!recognitionRef.current) {
      setError('Voice input is not supported in this browser.');
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
    } else {
      setError('');
      recognitionRef.current.start();
    }
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center' }}>
      <button
        type="button"
        onClick={toggleListening}
        title={isListening ? 'Stop voice input' : 'Start voice input'}
        aria-label={isListening ? 'Stop voice input' : 'Start voice input'}
        style={{
          height: '38px',
          width: '38px',
          borderRadius: '8px',
          border: '1px solid var(--border-color)',
          background: isListening
            ? 'var(--accent-purple)'
            : 'var(--bg-input)',
          color: 'var(--text-primary)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 0
        }}
      >
        {isListening ? '⏹️' : '🎤'}
      </button>

      {isListening && (
        <span
          style={{
            marginLeft: '8px',
            fontSize: '0.75rem',
            color: 'var(--text-muted)'
          }}
        >
          Listening...
        </span>
      )}

      {error && (
        <span
          style={{
            marginLeft: '8px',
            fontSize: '0.7rem',
            color: '#ef4444'
          }}
        >
          {error}
        </span>
      )}
    </div>
  );
}
