import { useCallback, useEffect, useState } from 'react';

import { AppHeader } from './components/AppHeader';
import { BuildTrackerCard } from './components/BuildTrackerCard';
import { ChatTranscript } from './components/ChatTranscript';
import { ComparisonCard } from './components/ComparisonCard';
import { MessageComposer } from './components/MessageComposer';
import { RetrievedSourcesPanel } from './components/RetrievedSourcesPanel';
import { TraceDetailsPanel } from './components/TraceDetailsPanel';
import { ValidationNotices } from './components/ValidationNotices';
import { useChatSession } from './hooks/useChatSession';
import { useVoiceConversation } from './hooks/useVoiceConversation';
import { fetchServiceReadiness } from './services/assistantApi';
import type { ServiceReadiness } from './services/assistantApi';

const READINESS_REFRESH_INTERVAL_MS = 30_000;

export default function App() {
  const { messages, activeBuild, latestReply, isAwaitingReply, errorMessage, askAssistant, resetSession } =
    useChatSession();
  const [readiness, setReadiness] = useState<ServiceReadiness | null>(null);

  const answerSpokenQuestion = useCallback(
    async (transcript: string) => (await askAssistant(transcript))?.reply ?? null,
    [askAssistant],
  );
  const voiceConversation = useVoiceConversation(answerSpokenQuestion);

  useEffect(() => {
    const refreshReadiness = () =>
      fetchServiceReadiness()
        .then(setReadiness)
        .catch(() => setReadiness(null));
    refreshReadiness();
    const intervalId = window.setInterval(refreshReadiness, READINESS_REFRESH_INTERVAL_MS);
    return () => window.clearInterval(intervalId);
  }, []);

  const startNewSession = () => {
    voiceConversation.stopVoiceMode();
    resetSession();
  };

  return (
    <div className="fixed inset-0 flex flex-col bg-gradient-to-br from-blue-950 via-slate-950 to-indigo-950 font-sans text-slate-100">
      <AppHeader
        readiness={readiness}
        isVoiceModeActive={voiceConversation.isVoiceModeActive}
        onStartNewSession={startNewSession}
      />

      <main className="flex min-h-0 flex-1">
        <section className="flex min-w-0 flex-1 flex-col">
          <ChatTranscript
            messages={messages}
            isAwaitingReply={isAwaitingReply}
            errorMessage={errorMessage}
            onAskSuggestedQuestion={askAssistant}
          />
          <MessageComposer
            isAwaitingReply={isAwaitingReply}
            isVoiceSupported={voiceConversation.isVoiceSupported}
            isVoiceModeActive={voiceConversation.isVoiceModeActive}
            isListening={voiceConversation.isListening}
            onSubmitQuestion={askAssistant}
            onToggleVoiceMode={voiceConversation.toggleVoiceMode}
          />
        </section>

        <aside className="thin-scrollbar hidden w-[400px] shrink-0 space-y-4 overflow-y-auto border-l border-white/5 bg-slate-950/40 p-6 lg:block">
          <BuildTrackerCard activeBuild={activeBuild} validation={latestReply?.validation ?? null} />
          <ValidationNotices validation={latestReply?.validation ?? null} />
          {latestReply?.comparison && <ComparisonCard comparison={latestReply.comparison} />}
          <RetrievedSourcesPanel sources={latestReply?.sources ?? []} />
          <TraceDetailsPanel traceId={latestReply?.traceId ?? null} />
        </aside>
      </main>
    </div>
  );
}
