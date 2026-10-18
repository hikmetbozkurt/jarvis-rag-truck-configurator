import { useState } from 'react';
import type { FormEvent } from 'react';
import { Mic, MicOff, Send } from 'lucide-react';

interface MessageComposerProps {
  isAwaitingReply: boolean;
  isVoiceSupported: boolean;
  isVoiceModeActive: boolean;
  isListening: boolean;
  onSubmitQuestion: (question: string) => void;
  onToggleVoiceMode: () => void;
}

export function MessageComposer({
  isAwaitingReply,
  isVoiceSupported,
  isVoiceModeActive,
  isListening,
  onSubmitQuestion,
  onToggleVoiceMode,
}: MessageComposerProps) {
  const [draftQuestion, setDraftQuestion] = useState('');

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!draftQuestion.trim()) return;
    onSubmitQuestion(draftQuestion);
    setDraftQuestion('');
  };

  const placeholder = isVoiceModeActive
    ? isListening
      ? 'Listening...'
      : 'Voice mode is on'
    : 'Ask about models, engines, pricing or EPA fuel economy...';

  return (
    <form onSubmit={handleSubmit} className="mx-auto flex w-full max-w-4xl items-center gap-3 px-4 pb-6 md:px-10">
      {isVoiceSupported && (
        <button
          type="button"
          onClick={onToggleVoiceMode}
          aria-label={isVoiceModeActive ? 'Stop voice mode' : 'Start voice mode'}
          className={`flex h-14 w-14 items-center justify-center rounded-2xl border transition ${
            isVoiceModeActive
              ? 'border-red-400 bg-red-500 text-white'
              : 'border-white/10 bg-white/5 text-slate-300 hover:bg-white/10'
          }`}
        >
          {isVoiceModeActive ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
        </button>
      )}
      <input
        value={draftQuestion}
        onChange={(event) => setDraftQuestion(event.target.value)}
        placeholder={placeholder}
        disabled={isAwaitingReply || isVoiceModeActive}
        maxLength={2000}
        className="h-14 flex-1 rounded-2xl border border-white/10 bg-white/[0.04] px-6 text-slate-100 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none disabled:opacity-50"
      />
      {!isVoiceModeActive && (
        <button
          type="submit"
          disabled={isAwaitingReply || !draftQuestion.trim()}
          className="flex h-14 items-center gap-2 rounded-2xl bg-blue-600 px-6 text-sm font-semibold text-white hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-500"
        >
          <Send className="h-4 w-4" />
          Send
        </button>
      )}
    </form>
  );
}
