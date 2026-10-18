import { useEffect, useRef } from 'react';

import type { ConversationMessage } from '../types/assistant';

const SUGGESTED_QUESTIONS = [
  'What is the best truck for logging?',
  'Can I get the 5.0L V8 with a manual transmission?',
  'Compare the F-150 and Silverado fuel economy',
  'What can I get under $45,000?',
];

interface ChatTranscriptProps {
  messages: ConversationMessage[];
  isAwaitingReply: boolean;
  errorMessage: string | null;
  onAskSuggestedQuestion: (question: string) => void;
}

function MessageBubble({ message }: { message: ConversationMessage }) {
  const isUserMessage = message.role === 'user';
  const reply = message.assistantReply;

  return (
    <div className={`flex ${isUserMessage ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-5 py-4 md:max-w-[70%] ${
          isUserMessage
            ? 'rounded-tr-none bg-blue-600 text-white'
            : 'rounded-tl-none border border-white/10 bg-white/[0.04] text-slate-100'
        }`}
      >
        <p className="whitespace-pre-line text-[15px] leading-relaxed">{message.content}</p>
        {reply && (
          <p className="mt-3 text-[11px] text-slate-500">
            {reply.intent.replace(/_/g, ' ')} · {(reply.latencyMs / 1000).toFixed(1)} s · {reply.sources.length} sources
          </p>
        )}
      </div>
    </div>
  );
}

function EmptyConversation({ onAskSuggestedQuestion }: Pick<ChatTranscriptProps, 'onAskSuggestedQuestion'>) {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center">
      <h2 className="mb-2 text-2xl font-bold text-white">How can I help with your truck?</h2>
      <p className="mb-8 max-w-md text-sm text-slate-400">
        I configure pickups against engineering rules and compare real-world EPA fuel economy. Every answer shows the
        documents it was grounded on.
      </p>
      <div className="grid w-full max-w-xl gap-2 sm:grid-cols-2">
        {SUGGESTED_QUESTIONS.map((question) => (
          <button
            key={question}
            type="button"
            onClick={() => onAskSuggestedQuestion(question)}
            className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-left text-sm text-slate-300 hover:border-blue-500/40 hover:bg-white/10"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}

export function ChatTranscript({ messages, isAwaitingReply, errorMessage, onAskSuggestedQuestion }: ChatTranscriptProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollContainerRef.current?.scrollTo({ top: scrollContainerRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, isAwaitingReply]);

  return (
    <div ref={scrollContainerRef} className="thin-scrollbar flex-1 space-y-6 overflow-y-auto px-4 py-8 md:px-12">
      {messages.length === 0 && !isAwaitingReply ? (
        <EmptyConversation onAskSuggestedQuestion={onAskSuggestedQuestion} />
      ) : (
        messages.map((message) => <MessageBubble key={message.messageId} message={message} />)
      )}

      {isAwaitingReply && (
        <div className="flex gap-1.5 px-2">
          {[0, 150, 300].map((delay) => (
            <span
              key={delay}
              className="h-2 w-2 animate-bounce rounded-full bg-blue-500"
              style={{ animationDelay: `${delay}ms` }}
            />
          ))}
        </div>
      )}

      {errorMessage && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {errorMessage}
        </div>
      )}
    </div>
  );
}
