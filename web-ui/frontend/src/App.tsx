import React, { useState, useEffect, useRef } from 'react';

interface Message {
  role: 'user' | 'jarvis';
  content: string;
  reasoning?: string;
}

interface ActiveBuild {
  model: string;
  engine: string;
  transmission: string;
  trim: string;
  mpg: string;
  status: string;
}

interface ComparisonData {
  vehicle_a: string;
  vehicle_b: string;
  efficiency_winner: string;
  power_winner: string;
  summary: string;
}

const App: React.FC = () => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isVoiceChatActive, setIsVoiceChatActive] = useState(false);
  const [currentReasoning, setCurrentReasoning] = useState<string>('');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [activeBuild, setActiveBuild] = useState<ActiveBuild>({
    model: 'None',
    engine: 'None',
    transmission: 'None',
    trim: 'None',
    mpg: 'N/A',
    status: 'Incomplete'
  });
  const [comparisonData, setComparisonData] = useState<ComparisonData | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  // Refs for Speech APIs to maintain state across renders
  const recognitionRef = useRef<any>(null);
  const isJarvisSpeakingRef = useRef(false);

  // Initialize Speech Recognition
  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false; // We want to stop after each phrase to process
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        console.log("Voice recognized:", transcript);
        if (transcript.trim()) {
          handleSend(transcript);
        }
      };

      recognitionRef.current.onend = () => {
        // Automatically restart listening if voice chat is active and Jarvis isn't speaking
        if (isVoiceChatActive && !isJarvisSpeakingRef.current && !isLoading) {
          try {
            console.log("Restarting recognition...");
            recognitionRef.current.start();
          } catch (e) {
            // Recognition might already be started
          }
        }
      };

      recognitionRef.current.onerror = (event: any) => {
        if (event.error !== 'no-speech') {
          console.error('Speech recognition error', event.error);
        }
        // If 'no-speech' (timeout) happens, we need to restart
        if (event.error === 'no-speech' && isVoiceChatActive && !isJarvisSpeakingRef.current) {
             try { recognitionRef.current.stop(); } catch(e) {}
             // Allow a tiny delay before restart to clear state
             setTimeout(() => {
                 try { recognitionRef.current.start(); } catch(e) {}
             }, 100);
        }
      };
    }
  }, [isVoiceChatActive, isLoading]);

  // Handle Jarvis Speaking
  const speak = (text: string) => {
    return new Promise<void>((resolve) => {
      window.speechSynthesis.cancel();
      isJarvisSpeakingRef.current = true;
      
      const utterance = new SpeechSynthesisUtterance(text);
      
      // Robust Voice Selection: Ensure we get a Male English Voice
      const loadVoicesAndSpeak = () => {
        const voices = window.speechSynthesis.getVoices();
        
        // 1. Try Preferred High-Quality Voices
        const preferredVoices = ['Daniel', 'Oliver', 'Google US English Male', 'Microsoft David', 'Alex'];
        let jarvisVoice = voices.find(v => preferredVoices.some(name => v.name.includes(name)));
        
        // 2. Fallback: Any English Male Voice (heuristic: name often contains 'Male')
        if (!jarvisVoice) {
           jarvisVoice = voices.find(v => v.lang.startsWith('en') && v.name.includes('Male'));
        }

        // 3. Fallback: Any English Voice (First available)
        if (!jarvisVoice) {
           jarvisVoice = voices.find(v => v.lang.startsWith('en'));
        }

        // Apply Voice
        if (jarvisVoice) {
          utterance.voice = jarvisVoice;
          utterance.lang = jarvisVoice.lang; // Force the lang of the chosen voice
        } else {
          // Absolute fallback if no English voice found (rare)
          utterance.lang = 'en-US';
        }

        utterance.rate = 1.0; 
        utterance.pitch = 0.9; 
        
        window.speechSynthesis.speak(utterance);
      };

      // Handle async voice loading (Chrome/Safari quirk)
      if (window.speechSynthesis.getVoices().length === 0) {
        window.speechSynthesis.onvoiceschanged = () => {
          loadVoicesAndSpeak();
          // Remove listener to prevent multiple triggers
          window.speechSynthesis.onvoiceschanged = null;
        };
      } else {
        loadVoicesAndSpeak();
      }
      
      utterance.onend = () => {
        isJarvisSpeakingRef.current = false;
        resolve();
        // Trigger listener restart if in voice mode
        if (isVoiceChatActive && recognitionRef.current) {
          try { recognitionRef.current.start(); } catch(e) {}
        }
      };

      utterance.onerror = (e) => {
        console.error("TTS Error:", e);
        isJarvisSpeakingRef.current = false;
        resolve();
      };
    });
  };

  const toggleVoiceChat = async () => {
    if (isVoiceChatActive) {
      setIsVoiceChatActive(false);
      window.speechSynthesis.cancel();
      recognitionRef.current?.stop();
    } else {
      // Request Microphone Permission explicitly
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        // Permission granted, we can stop the stream immediately as SpeechRecognition will manage it
        stream.getTracks().forEach(track => track.stop());
        
        setIsVoiceChatActive(true);
        // Initiation: Jarvis introduces himself
        const welcome = "Jarvis online. System check complete. All fleet data synced. How can I assist with your truck configuration today?";
        setMessages(prev => [...prev, { role: 'jarvis', content: welcome }]);
        await speak(welcome);
      } catch (err) {
        console.error("Microphone permission denied or not found:", err);
        const errorMsg = "Microphone access is required for Voice Mode. Please enable permissions in your browser settings.";
        setMessages(prev => [...prev, { role: 'jarvis', content: errorMsg }]);
        // Don't activate voice mode if permission fails
      }
    }
  };

  const clearHistory = () => {
    setMessages([]);
    setCurrentReasoning('');
    window.speechSynthesis.cancel();
    if (isVoiceChatActive) {
      toggleVoiceChat();
    }
  };

  const scrollToBottom = () => {
    const container = messagesContainerRef.current;
    if (container) {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: 'smooth'
      });
    }
  };

  useEffect(scrollToBottom, [messages]);

  const handleSend = async (voiceInput?: string) => {
    const textToSend = voiceInput || input;
    if (!textToSend.trim() || isLoading) return;

    // Stop listening while processing to avoid Jarvis hearing himself
    recognitionRef.current?.stop();

    const userMessage: Message = { role: 'user', content: textToSend };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: textToSend }),
      });

      const data = await response.json();
      
      // Try to parse active build from reasoning JSON
      try {
        // Cleaning the JSON string: remove markdown code blocks if present
        let cleanReasoning = data.reasoning.replace(/```json/g, "").replace(/```/g, "").trim();
        
        const reasoningData = JSON.parse(cleanReasoning);
        
        if (reasoningData.active_build) {
          console.log("Updating Active Build:", reasoningData.active_build);
          setActiveBuild(prev => ({
            ...prev,
            ...reasoningData.active_build
          }));
        }
        
        if (reasoningData.comparison) {
          setComparisonData(reasoningData.comparison);
        } else {
          setComparisonData(null);
        }
      } catch (e) {
        // Detailed error logging
        console.error("Failed to parse reasoning JSON:", e);
        console.log("Raw reasoning data:", data.reasoning);
      }

      const jarvisMessage: Message = {
        role: 'jarvis',
        content: data.response,
        reasoning: data.reasoning
      };

      setMessages(prev => [...prev, jarvisMessage]);
      setCurrentReasoning(data.reasoning);
      
      // In voice mode, Jarvis speaks back
      if (isVoiceChatActive) {
        await speak(data.response);
      }
      
    } catch (error) {
      const errMsg = 'Connection interrupted. Please ensure the backend engine is active.';
      setMessages(prev => [...prev, { role: 'jarvis', content: errMsg }]);
      if (isVoiceChatActive) await speak(errMsg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-[#020617] text-slate-100 flex flex-col font-sans overflow-hidden">
      {/* Dynamic Background */}
      <div className="absolute inset-0 pointer-events-none z-0" aria-hidden="true">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-950 via-[#020617] to-indigo-950 opacity-70"></div>
        <div className="absolute top-0 right-0 w-[520px] h-[520px] bg-blue-600/15 rounded-full blur-[140px] -translate-y-1/2 translate-x-1/3"></div>
        <div className="absolute bottom-0 left-0 w-[420px] h-[420px] bg-indigo-500/10 rounded-full blur-[120px] translate-y-1/3 -translate-x-1/4"></div>
      </div>

      {/* Header */}
      <header className="px-6 py-4 border-b border-white/5 flex justify-between items-center bg-[#020617]/80 backdrop-blur-xl z-20 shadow-xl">
        <div className="flex items-center space-x-4">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-xl transition-all duration-500 shadow-2xl border ${
            isVoiceChatActive ? 'bg-blue-600 border-blue-400 animate-pulse scale-110 shadow-blue-500/40' : 'bg-slate-800 border-white/10'
          }`}>
            {isVoiceChatActive ? '🎙️' : '🚛'}
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white flex items-center">
              Jarvis
              {isVoiceChatActive && <span className="ml-2 px-1.5 py-0.5 rounded text-[8px] bg-red-500/20 text-red-400 border border-red-500/30 uppercase tracking-widest animate-pulse">Live Voice</span>}
            </h1>
            <p className="text-[10px] uppercase tracking-[0.15em] text-slate-500 font-semibold">Specialist AI Advisor</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button 
            onClick={clearHistory}
            className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 hover:bg-red-500/10 hover:border-red-500/20 text-[10px] font-bold text-slate-400 hover:text-red-400 transition-all uppercase tracking-wider"
          >
            Clear Session
          </button>
          <div className="hidden sm:flex items-center space-x-2 text-[11px] font-bold text-slate-400 bg-white/5 px-3 py-1.5 rounded-full border border-white/10">
            <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></span>
            <span className="opacity-80 uppercase tracking-tighter">Engine Online</span>
          </div>
        </div>
      </header>

      <main className="flex-1 flex overflow-hidden relative z-10 min-h-0">
        {/* Chat Area */}
        <div className="flex-1 flex flex-col min-w-0 min-h-0 relative">
          <div
            ref={messagesContainerRef}
            className="flex-1 overflow-y-auto px-4 md:px-12 py-8 space-y-8 custom-scrollbar"
          >
            {messages.length === 0 && !isVoiceChatActive && (
              <div className="h-full flex flex-col items-center justify-center text-center">
                <div className="w-24 h-24 bg-blue-600/10 rounded-3xl flex items-center justify-center text-5xl mb-6 border border-blue-500/20 shadow-inner animate-pulse">⚡</div>
                <h2 className="text-3xl font-bold text-white mb-2 tracking-tight">System Online</h2>
                <div className="flex space-x-2 mb-6">
                    <span className="text-xl">🚛</span>
                    <span className="text-xl">🔧</span>
                    <span className="text-xl">📊</span>
                </div>
                <p className="text-slate-400 max-w-sm text-sm leading-relaxed mb-8 font-medium">
                  I am Jarvis, your Advanced Vehicle Engineering Assistant. 
                  <br/><br/>
                  I can configure custom trucks, analyze EPA efficiency data, and perform head-to-head comparisons.
                </p>
                <div className="flex space-x-3">
                    <button onClick={() => toggleVoiceChat()} className="px-5 py-2.5 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 text-xs font-bold uppercase tracking-widest rounded-xl border border-blue-500/30 transition-all">
                        🎙️ Initialize Voice
                    </button>
                    <button onClick={() => handleSend("Compare F-150 and Silverado")} className="px-5 py-2.5 bg-white/5 hover:bg-white/10 text-slate-300 text-xs font-bold uppercase tracking-widest rounded-xl border border-white/10 transition-all">
                        ⚖️ Run Comparison
                    </button>
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-4 duration-500`}>
                <div className={`max-w-[80%] md:max-w-[65%] p-5 rounded-3xl transition-all shadow-2xl ${
                  msg.role === 'user' 
                    ? 'bg-blue-600 text-white rounded-tr-none border border-blue-400/30' 
                    : 'bg-white/[0.03] backdrop-blur-md border border-white/10 rounded-tl-none'
                }`}>
                  <span className={`text-[8px] font-black uppercase tracking-[0.2em] mb-2 block opacity-50 ${msg.role === 'user' ? 'text-blue-100' : 'text-blue-400'}`}>
                    {msg.role === 'user' ? 'User' : 'Jarvis - AI Consultant'}
                  </span>
                  <p className="text-[15px] leading-relaxed font-medium">{msg.content}</p>
                </div>
              </div>
            ))}
            
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-white/[0.03] backdrop-blur-md border border-white/10 p-6 rounded-3xl rounded-tl-none flex space-x-2">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Voice & Input Footer */}
          <div className="p-6 md:p-10 bg-gradient-to-t from-[#020617] via-[#020617]/95 to-transparent">
            <div className="max-w-4xl mx-auto flex items-center space-x-4">
              {/* GPT-Style Voice Toggle */}
              <button
                onClick={toggleVoiceChat}
                className={`group relative h-[64px] px-6 flex items-center justify-center rounded-2xl transition-all duration-500 border shadow-2xl overflow-hidden ${
                  isVoiceChatActive 
                    ? 'bg-red-500 border-red-400 text-white' 
                    : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10 hover:border-blue-500/50'
                }`}
              >
                <div className="flex items-center space-x-3 z-10">
                  <span className="text-xl">{isVoiceChatActive ? '⏹️' : '🎙️'}</span>
                  <span className="text-xs font-black uppercase tracking-widest hidden md:block">
                    {isVoiceChatActive ? 'Stop Voice Chat' : 'Voice Mode'}
                  </span>
                </div>
                {isVoiceChatActive && (
                  <div className="absolute inset-0 bg-gradient-to-r from-red-600 to-red-400 animate-pulse"></div>
                )}
              </button>

              <div className="relative flex-1">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                  placeholder={isVoiceChatActive ? "Jarvis is listening..." : "Type technical specifications..."}
                  disabled={isLoading || isVoiceChatActive}
                  className="w-full bg-white/[0.03] border border-white/10 rounded-2xl py-5 px-8 focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all text-base disabled:opacity-50 shadow-inner"
                />
              </div>
              
              {!isVoiceChatActive && (
                <button
                  onClick={() => handleSend()}
                  disabled={isLoading || !input.trim()}
                  className="h-[64px] px-8 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 text-white rounded-2xl font-black uppercase tracking-widest text-[11px] transition-all shadow-lg active:scale-95 border border-blue-400/20"
                >
                  Send 🚀
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Sidebar Console */}
        <aside className={`${isSidebarOpen ? 'flex' : 'hidden'} lg:w-[450px] bg-[#020617]/50 border-l border-white/5 flex-col p-10 backdrop-blur-3xl transition-all duration-500 z-20 min-h-0`}>
          <div className="flex items-center justify-between mb-10">
            <h2 className="text-[10px] font-black text-blue-400 uppercase tracking-[0.3em]">Decision Engine</h2>
            <div className="flex space-x-1">
              <div className="w-1 h-1 bg-blue-500 rounded-full"></div>
              <div className="w-1 h-1 bg-blue-500 rounded-full opacity-50"></div>
              <div className="w-1 h-1 bg-blue-500 rounded-full opacity-20"></div>
            </div>
          </div>
          
          <div className="flex-1 overflow-y-auto space-y-10 custom-scrollbar pr-2">
            {/* Active Build Tracker */}
            {!comparisonData ? (
              <section className="bg-blue-600/5 rounded-3xl p-6 border border-blue-500/20 shadow-inner relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                  <span className="text-4xl">🛠️</span>
                </div>
                <h3 className="text-[9px] font-black text-blue-400 uppercase tracking-widest mb-6 flex items-center">
                  <span className="w-2 h-2 bg-blue-500 rounded-full mr-2 animate-pulse"></span>
                  Active Build Tracker
                </h3>
                
                <div className="space-y-4">
                  {[
                    { label: "Model", value: activeBuild.model },
                    { label: "Trim", value: activeBuild.trim },
                    { label: "Engine", value: activeBuild.engine },
                    { label: "Transmission", value: activeBuild.transmission },
                    { label: "Efficiency", value: activeBuild.mpg + " MPG" }
                  ].map((item, idx) => (
                    <div key={idx} className="flex justify-between items-end border-b border-white/5 pb-2">
                      <span className="text-[10px] text-slate-500 font-bold uppercase tracking-tight">{item.label}</span>
                      <span className={`text-xs font-mono font-bold ${item.value === 'None' || item.value === 'N/A MPG' ? 'text-slate-600' : 'text-white'}`}>
                        {item.value}
                      </span>
                    </div>
                  ))}
                  
                  <div className="mt-6 pt-2 flex items-center justify-between">
                    <span className="text-[10px] text-slate-500 font-bold uppercase">Configuration Status</span>
                    <span className={`px-2 py-0.5 rounded text-[8px] font-black uppercase tracking-tighter border ${
                      activeBuild.status === 'Valid' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' :
                      activeBuild.status === 'Invalid' ? 'bg-red-500/10 border-red-500/30 text-red-400' :
                      'bg-amber-500/10 border-amber-500/30 text-amber-400'
                    }`}>
                      {activeBuild.status}
                    </span>
                  </div>
                </div>
              </section>
            ) : (
              /* Comparison Mode Widget */
              <section className="bg-indigo-600/10 rounded-3xl p-6 border border-indigo-500/30 shadow-inner relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                  <span className="text-4xl">⚖️</span>
                </div>
                <h3 className="text-[9px] font-black text-indigo-400 uppercase tracking-widest mb-6 flex items-center">
                  <span className="w-2 h-2 bg-indigo-500 rounded-full mr-2 animate-pulse"></span>
                  Comparison Analysis
                </h3>
                
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div className="text-center p-2 bg-black/20 rounded-xl">
                    <p className="text-[8px] text-slate-500 uppercase font-bold">Vehicle A</p>
                    <p className="text-[10px] font-bold text-white truncate">{comparisonData.vehicle_a}</p>
                  </div>
                  <div className="text-center p-2 bg-black/20 rounded-xl">
                    <p className="text-[8px] text-slate-500 uppercase font-bold">Vehicle B</p>
                    <p className="text-[10px] font-bold text-white truncate">{comparisonData.vehicle_b}</p>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex justify-between items-center border-b border-white/5 pb-2">
                     <span className="text-[9px] text-slate-400 font-bold uppercase">Efficiency Winner</span>
                     <span className="text-[10px] text-emerald-400 font-bold">{comparisonData.efficiency_winner}</span>
                  </div>
                  <div className="flex justify-between items-center border-b border-white/5 pb-2">
                     <span className="text-[9px] text-slate-400 font-bold uppercase">Power Winner</span>
                     <span className="text-[10px] text-amber-400 font-bold">{comparisonData.power_winner}</span>
                  </div>
                </div>

                <div className="mt-4 p-3 bg-white/5 rounded-xl border border-white/5">
                  <p className="text-[9px] text-slate-300 italic leading-relaxed">"{comparisonData.summary}"</p>
                </div>
              </section>
            )}

            <section>
              <h3 className="text-[9px] font-black text-slate-500 uppercase tracking-widest mb-4 italic">// Neural Processing</h3>
              <div className="bg-black/40 rounded-3xl p-8 border border-white/5 font-mono text-[11px] text-blue-300/80 shadow-2xl leading-relaxed relative overflow-hidden group">
                <div className="absolute -top-10 -right-10 w-32 h-32 bg-blue-500/10 blur-[50px] rounded-full"></div>
                {currentReasoning ? (
                  <pre className="whitespace-pre-wrap">{currentReasoning}</pre>
                ) : (
                  <div className="h-full py-12 flex flex-col items-center justify-center text-slate-600 text-center">
                    <span className="text-2xl mb-4 opacity-20">📡</span>
                    <p className="text-[10px] uppercase tracking-widest">Awaiting active data stream...</p>
                  </div>
                )}
              </div>
            </section>
            
            <section className="grid grid-cols-1 gap-3">
              <h3 className="text-[9px] font-black text-slate-500 uppercase tracking-widest italic mb-1">// System Telemetry</h3>
              {[
                { name: "RAG Context", val: "5 Docs", status: "Active" },
                { name: "EPA Sync", val: "3153 Records", status: "Loaded" },
                { name: "Voice Protocol", val: "STT/TTS", status: isVoiceChatActive ? "ON" : "STBY" }
              ].map(item => (
                <div key={item.name} className="flex justify-between items-center p-4 bg-white/5 rounded-2xl border border-white/5 hover:bg-white/[0.08] transition-all">
                  <div>
                    <p className="text-[10px] font-bold text-slate-300">{item.name}</p>
                    <p className="text-[9px] text-slate-500">{item.val}</p>
                  </div>
                  <span className={`text-[8px] font-black px-2 py-1 rounded border ${
                    item.status === 'ON' || item.status === 'Active' ? 'bg-blue-500/10 border-blue-500/30 text-blue-400' : 'bg-white/5 border-white/10 text-slate-500'
                  }`}>
                    {item.status}
                  </span>
                </div>
              ))}
            </section>
          </div>
        </aside>
      </main>
    </div>
  );
};

export default App;
