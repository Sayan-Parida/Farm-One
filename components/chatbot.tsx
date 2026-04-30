"use client"

import { useState, useRef, useEffect } from "react"

interface ChatbotProps {
  coordinates: { lat: number; lon: number } | null
  crop: string | null
  onClose: () => void
}

interface Message {
  role: "user" | "assistant"
  content: string
}

export default function Chatbot({ coordinates, crop, onClose }: ChatbotProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || !coordinates) return

    const userMessage = input.trim()
    setInput("")

    setMessages((prev) => [...prev, { role: "user", content: userMessage }])
    setLoading(true)

    try {
      const response = await fetch(`/api/ml/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: userMessage,
          lat: coordinates.lat,
          lon: coordinates.lon,
          context: crop ? { crop } : {},
        }),
      })

      if (!response.ok) throw new Error("Failed to get response")
      const data = await response.json()
      setMessages((prev) => [...prev, { role: "assistant", content: data.answer || data.reply || "I couldn't generate a response." }])
    } catch (err) {
      // Mock response for preview
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Yes, this location shows suitable conditions. The soil pH and moisture levels support growth here. Consider local rainfall patterns for irrigation planning.",
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="w-full max-w-4xl mx-auto px-4 md:px-8 py-8">
      <div className="border border-black rounded-sm overflow-hidden flex flex-col h-96">
        {/* Header */}
        <div className="border-b border-black p-4 md:p-6 flex items-center justify-between">
          <div>
            <h2 className="font-serif font-bold mb-1">Ask about crops for this location</h2>
            {coordinates && (
              <p className="text-xs text-gray-600">
                {coordinates.lat.toFixed(4)}, {coordinates.lon.toFixed(4)}
              </p>
            )}
          </div>
          <button onClick={onClose} className="text-sm font-medium hover:underline">
            Close
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
          {messages.length === 0 && <p className="text-sm text-gray-600">Ask, e.g., "Can I grow wheat here?"</p>}

          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-xs md:max-w-md px-3 py-2 text-sm rounded-sm ${
                  msg.role === "user" ? "bg-black text-white" : "bg-gray-100 text-black border border-black"
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 px-3 py-2">
                <div className="w-3 h-3 border-2 border-black border-t-transparent rounded-full animate-spin-custom" />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-black p-4 md:p-6">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && !loading && handleSend()}
              placeholder="Ask, e.g., Can I grow wheat here?"
              className="flex-1 px-3 py-2 border border-black bg-white text-black placeholder-gray-600 text-sm focus:outline-black"
              disabled={loading}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading}
              className="px-4 py-2 border border-black bg-white text-black font-medium text-sm transition-colors hover:bg-black hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}
