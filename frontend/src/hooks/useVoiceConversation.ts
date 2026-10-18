import { useCallback, useEffect, useRef, useState } from 'react';

type TranscriptHandler = (transcript: string) => Promise<string | null>;

interface BrowserSpeechRecognition {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onend: (() => void) | null;
  onerror: ((event: { error: string }) => void) | null;
}

type SpeechRecognitionConstructor = new () => BrowserSpeechRecognition;

const PREFERRED_VOICE_NAMES = ['Daniel', 'Oliver', 'Google US English', 'Microsoft David', 'Alex'];

function findSpeechRecognitionConstructor(): SpeechRecognitionConstructor | null {
  const speechWindow = window as unknown as {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  };
  return speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition ?? null;
}

function chooseEnglishVoice(): SpeechSynthesisVoice | undefined {
  const voices = window.speechSynthesis.getVoices();
  return (
    voices.find((voice) => PREFERRED_VOICE_NAMES.some((name) => voice.name.includes(name))) ??
    voices.find((voice) => voice.lang.startsWith('en'))
  );
}

export function useVoiceConversation(handleTranscript: TranscriptHandler) {
  const [isVoiceModeActive, setIsVoiceModeActive] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const isVoiceModeActiveRef = useRef(false);
  const isBusyRef = useRef(false);
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const transcriptHandlerRef = useRef(handleTranscript);
  transcriptHandlerRef.current = handleTranscript;

  const isVoiceSupported = findSpeechRecognitionConstructor() !== null && 'speechSynthesis' in window;

  const speakText = useCallback(
    (text: string) =>
      new Promise<void>((resolve) => {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        const englishVoice = chooseEnglishVoice();
        if (englishVoice) utterance.voice = englishVoice;
        utterance.lang = englishVoice?.lang ?? 'en-US';
        utterance.pitch = 0.9;
        utterance.onend = () => {
          setIsSpeaking(false);
          resolve();
        };
        utterance.onerror = () => {
          setIsSpeaking(false);
          resolve();
        };
        setIsSpeaking(true);
        window.speechSynthesis.speak(utterance);
      }),
    [],
  );

  const startListening = useCallback(() => {
    if (!isVoiceModeActiveRef.current || isBusyRef.current || !recognitionRef.current) return;
    try {
      recognitionRef.current.start();
      setIsListening(true);
    } catch {
      setIsListening(false);
    }
  }, []);

  useEffect(() => {
    const RecognitionConstructor = findSpeechRecognitionConstructor();
    if (!RecognitionConstructor) return;

    const recognition = new RecognitionConstructor();
    recognition.lang = 'en-US';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onresult = async (event) => {
      const transcript = event.results[0]?.[0]?.transcript?.trim();
      if (!transcript) return;
      isBusyRef.current = true;
      setIsListening(false);
      const replyText = await transcriptHandlerRef.current(transcript);
      if (replyText && isVoiceModeActiveRef.current) await speakText(replyText);
      isBusyRef.current = false;
      startListening();
    };
    recognition.onend = () => {
      setIsListening(false);
      if (!isBusyRef.current) startListening();
    };
    recognition.onerror = (event) => {
      if (event.error !== 'no-speech') console.warn('Speech recognition error:', event.error);
    };

    recognitionRef.current = recognition;
    return () => {
      isVoiceModeActiveRef.current = false;
      recognition.onend = null;
      recognition.stop();
      window.speechSynthesis.cancel();
    };
  }, [speakText, startListening]);

  const stopVoiceMode = useCallback(() => {
    isVoiceModeActiveRef.current = false;
    setIsVoiceModeActive(false);
    recognitionRef.current?.stop();
    window.speechSynthesis.cancel();
  }, []);

  const toggleVoiceMode = useCallback(async (): Promise<boolean> => {
    if (isVoiceModeActiveRef.current) {
      stopVoiceMode();
      return true;
    }
    try {
      const microphoneStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      microphoneStream.getTracks().forEach((track) => track.stop());
    } catch {
      return false;
    }
    isVoiceModeActiveRef.current = true;
    setIsVoiceModeActive(true);
    startListening();
    return true;
  }, [startListening, stopVoiceMode]);

  return { isVoiceSupported, isVoiceModeActive, isListening, isSpeaking, toggleVoiceMode, stopVoiceMode };
}
