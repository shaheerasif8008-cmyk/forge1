import { useEffect, useMemo, useRef, useState } from "react";
import config from "../config";
import { useSession } from "../components/SessionManager";

type Msg = { role: "user" | "assistant"; content: string };

export default function AssistantPanel() {
  const { token } = useSession();
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Msg[]>([
    { role: "assistant", content: "Hi! I’m your Forge assistant. Ask me anything about onboarding or configuration." },
  ]);
  const [busy, setBusy] = useState(false);
  const scroller = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight });
  }, [messages]);

  const headers = useMemo(
    () => ({ "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) }),
    [token],
  );

  const ask = async () => {
    if (!input.trim()) return;
    const q = input;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: q }]);
    setBusy(true);
    try {
      const resp = await fetch(`${config.apiUrl}/api/v1/ai/execute`, {
        method: "POST",
        headers,
        body: JSON.stringify({ task: `User asked: ${q}. If they ask how to connect a tool, cite the steps and link to /marketplace or /admin/tools. If they want to open a ticket, say 'Opening ticket...' and return a short summary.`, task_type: "general" }),
      });
      if (resp.ok) {
        const data = (await resp.json()) as { output: string };
        setMessages((m) => [...m, { role: "assistant", content: data.output || "" }]);
      } else {
        setMessages((m) => [...m, { role: "assistant", content: "Sorry, I ran into an error." }]);
      }
    } catch {
      setMessages((m) => [...m, { role: "assistant", content: "Network error." }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col h-full border-l bg-white">
      <div className="p-3 border-b font-medium">Assistant</div>
      <div ref={scroller} className="flex-1 overflow-auto space-y-2 p-3">
        {messages.map((m, i) => (
          <div key={i} className={`text-sm ${m.role === "assistant" ? "text-gray-800" : "text-gray-900"}`}>
            <span className="font-medium mr-1">{m.role === "assistant" ? "Assistant:" : "You:"}</span>
            <span className="whitespace-pre-wrap">{m.content}</span>
          </div>
        ))}
      </div>
      <div className="p-3 border-t flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void ask();
            }
          }}
          placeholder="Ask how to connect X, or type 'open ticket'"
          className="border rounded px-3 py-2 flex-1"
        />
        <button disabled={busy} onClick={() => void ask()} className="px-3 py-2 bg-blue-600 text-white rounded disabled:bg-blue-300">
          {busy ? "Thinking…" : "Send"}
        </button>
      </div>
    </div>
  );
}


