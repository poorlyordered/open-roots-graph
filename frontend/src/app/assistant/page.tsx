"use client"

import { useRef, useState, useEffect } from "react"
import type { ChatMessage as ChatMessageType, ChatMode, StreamChunk } from "@/lib/types"
import { streamChat } from "@/lib/api"
import ChatMessage from "@/components/assistant/ChatMessage"
import SuggestedQuestions from "@/components/assistant/SuggestedQuestions"

const modeConfig: Record<ChatMode, { label: string; color: string; desc: string }> = {
  query: {
    label: "Query",
    color: "var(--accent)",
    desc: "Ask questions about your family tree data",
  },
  hypothesis: {
    label: "Hypothesis",
    color: "var(--accent-orange)",
    desc: "Discover possible connections and patterns",
  },
  research: {
    label: "Research",
    color: "var(--accent-pink)",
    desc: "Identify data gaps and next steps",
  },
}

export default function AssistantPage() {
  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [input, setInput] = useState("")
  const [mode, setMode] = useState<ChatMode>("query")
  const [isStreaming, setIsStreaming] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const handleSend = async (text?: string, sendMode?: ChatMode) => {
    const msg = text || input.trim()
    const activeMode = sendMode || mode
    if (!msg || isStreaming) return

    setInput("")
    const userMessage: ChatMessageType = { role: "user", content: msg }

    setMessages((prev) => [...prev, userMessage])
    setIsStreaming(true)

    let assistantContent = ""
    let cypherQuery: string | undefined
    let queryResults: Record<string, unknown>[] | undefined

    // Add placeholder assistant message
    const assistantIdx = messages.length + 1
    setMessages((prev) => [...prev, { role: "assistant", content: "" }])

    try {
      await streamChat(
        msg,
        [...messages, userMessage],
        activeMode,
        (chunk: StreamChunk) => {
          switch (chunk.type) {
            case "text":
              assistantContent += chunk.content
              setMessages((prev) => {
                const updated = [...prev]
                updated[assistantIdx] = {
                  ...updated[assistantIdx],
                  content: assistantContent,
                }
                return updated
              })
              break

            case "cypher":
              cypherQuery = chunk.content
              setMessages((prev) => {
                const updated = [...prev]
                updated[assistantIdx] = {
                  ...updated[assistantIdx],
                  cypherQuery: chunk.content,
                }
                return updated
              })
              break

            case "data":
              try {
                queryResults = JSON.parse(chunk.content)
                setMessages((prev) => {
                  const updated = [...prev]
                  updated[assistantIdx] = {
                    ...updated[assistantIdx],
                    queryResults,
                  }
                  return updated
                })
              } catch {
                // skip malformed data
              }
              break

            case "error":
              assistantContent += `\n⚠ ${chunk.content}`
              setMessages((prev) => {
                const updated = [...prev]
                updated[assistantIdx] = {
                  ...updated[assistantIdx],
                  content: assistantContent,
                }
                return updated
              })
              break

            case "done":
              break
          }
        },
      )
    } catch {
      assistantContent += "\n⚠ Connection error. Please try again."
      setMessages((prev) => {
        const updated = [...prev]
        updated[assistantIdx] = {
          ...updated[assistantIdx],
          content: assistantContent,
        }
        return updated
      })
    }

    setIsStreaming(false)
    inputRef.current?.focus()
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div
        className="flex items-center justify-between px-6 py-3 border-b flex-shrink-0"
        style={{ borderColor: "var(--border)", background: "var(--surface)" }}
      >
        <div>
          <h1 className="text-lg font-bold">Research Assistant</h1>
          <p className="text-xs" style={{ color: "#666" }}>
            {modeConfig[mode].desc}
          </p>
        </div>
        <div className="flex gap-1">
          {(Object.entries(modeConfig) as [ChatMode, typeof modeConfig.query][]).map(
            ([key, cfg]) => (
              <button
                key={key}
                onClick={() => setMode(key)}
                className="text-xs px-3 py-1.5 rounded-lg transition-colors"
                style={{
                  background: mode === key ? cfg.color + "22" : "transparent",
                  color: mode === key ? cfg.color : "#666",
                  border: mode === key ? `1px solid ${cfg.color}44` : "1px solid transparent",
                }}
              >
                {cfg.label}
              </button>
            ),
          )}
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6">
        {messages.length === 0 ? (
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-8">
              <div className="text-4xl mb-3" style={{ color: "var(--accent)" }}>◎</div>
              <h2 className="text-lg font-semibold mb-1">Research Assistant</h2>
              <p className="text-sm" style={{ color: "#666" }}>
                Ask questions about your family tree, explore hypotheses, or plan research.
              </p>
            </div>
            <SuggestedQuestions onSelect={(text, m) => handleSend(text, m)} />
          </div>
        ) : (
          messages.map((msg, i) => (
            <ChatMessage
              key={i}
              message={msg}
              isStreaming={isStreaming && i === messages.length - 1 && msg.role === "assistant"}
            />
          ))
        )}
      </div>

      {/* Input */}
      <div
        className="px-6 py-4 border-t flex-shrink-0"
        style={{ borderColor: "var(--border)", background: "var(--surface)" }}
      >
        <div className="max-w-3xl mx-auto flex gap-3">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
            placeholder={
              isStreaming
                ? "Waiting for response..."
                : "Ask about your family tree..."
            }
            disabled={isStreaming}
            className="flex-1 px-4 py-2.5 rounded-xl text-sm border"
            style={{
              background: "#0a0a1a",
              borderColor: "var(--border)",
              color: "var(--foreground)",
            }}
          />
          <button
            onClick={() => handleSend()}
            disabled={isStreaming || !input.trim()}
            className="px-5 py-2.5 rounded-xl text-sm font-medium transition-opacity"
            style={{
              background: modeConfig[mode].color,
              color: "#000",
              opacity: isStreaming || !input.trim() ? 0.4 : 1,
            }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}
