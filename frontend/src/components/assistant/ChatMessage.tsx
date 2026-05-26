"use client"

import { useState } from "react"
import type { ChatMessage as ChatMessageType } from "@/lib/types"

interface Props {
  message: ChatMessageType
  isStreaming?: boolean
}

export default function ChatMessage({ message, isStreaming }: Props) {
  const [showCypher, setShowCypher] = useState(false)
  const isUser = message.role === "user"

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className="max-w-[80%] rounded-xl px-4 py-3 text-sm"
        style={{
          background: isUser ? "var(--accent)" : "var(--surface)",
          color: isUser ? "#000" : "var(--foreground)",
          border: isUser ? "none" : "1px solid var(--border)",
        }}
      >
        {/* Message text */}
        <div className="whitespace-pre-wrap">{message.content}{isStreaming && "▊"}</div>

        {/* Cypher query (collapsible) */}
        {message.cypherQuery && (
          <div className="mt-3">
            <button
              onClick={() => setShowCypher(!showCypher)}
              className="text-[11px] px-2 py-0.5 rounded"
              style={{ background: "rgba(255,255,255,0.1)", color: "#888" }}
            >
              {showCypher ? "Hide" : "Show"} Cypher Query
            </button>
            {showCypher && (
              <pre
                className="mt-2 p-3 rounded-lg text-[11px] overflow-x-auto"
                style={{ background: "#0a0a1a", color: "var(--accent)" }}
              >
                {message.cypherQuery}
              </pre>
            )}
          </div>
        )}

        {/* Query results table */}
        {message.queryResults && message.queryResults.length > 0 && (
          <div className="mt-3 overflow-x-auto">
            <table className="text-[11px] w-full">
              <thead>
                <tr>
                  {Object.keys(message.queryResults[0]).map((key) => (
                    <th
                      key={key}
                      className="text-left px-2 py-1 border-b"
                      style={{ borderColor: "var(--border)", color: "#888" }}
                    >
                      {key}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {message.queryResults.map((row, i) => (
                  <tr key={i}>
                    {Object.values(row).map((val, j) => (
                      <td
                        key={j}
                        className="px-2 py-1 border-b"
                        style={{ borderColor: "var(--border)" }}
                      >
                        {typeof val === "object" ? JSON.stringify(val) : String(val ?? "—")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-[10px] mt-1" style={{ color: "#555" }}>
              {message.queryResults.length} row{message.queryResults.length !== 1 ? "s" : ""}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
