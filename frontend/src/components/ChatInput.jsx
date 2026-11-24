import React, { useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';

export default function ChatInput({ input, setInput, onSend, isLoading }) {
  const textareaRef = useRef(null);

  useEffect(() => {
    if (!isLoading && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isLoading]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isLoading && input.trim()) {
        onSend();
      }
    }
  };

  const isOverLimit = input.length > 4000;
  const canSend = input.trim().length > 0 && !isOverLimit && !isLoading;

  return (
    <footer className="border-t border-slate-800 bg-slate-900/90 backdrop-blur-md p-4">
      <div className="max-w-4xl mx-auto">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (canSend) onSend();
          }}
          className="relative flex items-end gap-2 rounded-2xl border border-slate-700 bg-slate-800/90 p-2 shadow-lg focus-within:border-blue-500 transition-all"
        >
          <textarea
            ref={textareaRef}
            data-testid="chat-input"
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            placeholder={isLoading ? 'Generating response...' : 'Type a message... (Enter to send)'}
            className="flex-1 max-h-36 resize-none bg-transparent px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none disabled:opacity-60"
            style={{ minHeight: '38px' }}
          />

          <button
            data-testid="send-button"
            type="submit"
            disabled={!canSend}
            className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600 text-white transition-all hover:bg-blue-500 active:scale-95 disabled:bg-slate-700 disabled:text-slate-500 disabled:cursor-not-allowed shadow-md"
            title="Send Message"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin text-white" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
        </form>

        <div className="flex items-center justify-between px-2 pt-2 text-[11px] text-slate-500">
          <span>Enter to send, Shift+Enter for new line</span>
          <span className={isOverLimit ? 'text-red-400 font-semibold' : ''}>
            {input.length} / 4000
          </span>
        </div>
      </div>
    </footer>
  );
}
