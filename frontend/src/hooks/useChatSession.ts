import { useCallback, useRef, useState } from 'react';

import { sendChatMessage } from '../services/assistantApi';
import { EMPTY_VEHICLE_BUILD } from '../types/assistant';
import type { AssistantReply, ConversationMessage, VehicleBuild } from '../types/assistant';

const createIdentifier = () => crypto.randomUUID();

export function useChatSession() {
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [activeBuild, setActiveBuild] = useState<VehicleBuild>(EMPTY_VEHICLE_BUILD);
  const [latestReply, setLatestReply] = useState<AssistantReply | null>(null);
  const [isAwaitingReply, setIsAwaitingReply] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const sessionIdRef = useRef(createIdentifier());

  const askAssistant = useCallback(
    async (question: string): Promise<AssistantReply | null> => {
      const trimmedQuestion = question.trim();
      if (!trimmedQuestion || isAwaitingReply) return null;

      const history = messages.map(({ role, content }) => ({ role, content }));
      setMessages((previous) => [...previous, { messageId: createIdentifier(), role: 'user', content: trimmedQuestion }]);
      setIsAwaitingReply(true);
      setErrorMessage(null);

      try {
        const assistantReply = await sendChatMessage({
          message: trimmedQuestion,
          history,
          activeBuild,
          sessionId: sessionIdRef.current,
        });
        setMessages((previous) => [
          ...previous,
          { messageId: createIdentifier(), role: 'assistant', content: assistantReply.reply, assistantReply },
        ]);
        setActiveBuild(assistantReply.activeBuild);
        setLatestReply(assistantReply);
        return assistantReply;
      } catch (requestError) {
        setErrorMessage(requestError instanceof Error ? requestError.message : 'The assistant is not reachable.');
        return null;
      } finally {
        setIsAwaitingReply(false);
      }
    },
    [activeBuild, isAwaitingReply, messages],
  );

  const resetSession = useCallback(() => {
    setMessages([]);
    setActiveBuild(EMPTY_VEHICLE_BUILD);
    setLatestReply(null);
    setErrorMessage(null);
    sessionIdRef.current = createIdentifier();
  }, []);

  return { messages, activeBuild, latestReply, isAwaitingReply, errorMessage, askAssistant, resetSession };
}
