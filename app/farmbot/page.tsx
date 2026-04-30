"use client"

import { useState } from "react"
import Navbar from "@/components/navbar"
import Footer from "@/components/footer"
import { Send } from "lucide-react"

export default function FarmBot() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello! I'm FarmBot, your agricultural assistant. I can help you with crop recommendations, soil management, weather insights, and farming best practices. How can I help you today?",
      timestamp: "03:58",
    },
  ])
  const [input, setInput] = useState("")

  const handleSend = async () => {
    if (!input.trim()) return

    // Add user message
    setMessages([...messages, { role: "user", content: input, timestamp: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }) }])
    setInput("")

    // Connect to backend API
    try {
      const response = await fetch(`/api/ml/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: input })
      })

      if (!response.ok) {
        throw new Error("Failed to get response")
      }

      const data = await response.json()

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          timestamp: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
        },
      ])
    } catch (err) {
      console.error("FarmBot Error:", err)
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I'm having trouble connecting to the server. Please try again later.",
          timestamp: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
        },
      ])
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Navbar />

      <main className="flex-1">
        <div className="w-full max-w-7xl mx-auto px-4 md:px-8 py-12">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Info Sidebar */}
            <div className="lg:col-span-1">
              <div className="bg-white rounded-lg border border-gray-200 p-6 sticky top-24">
                <h2 className="text-xl font-serif font-bold mb-6">FarmBot Info</h2>

                <div className="mb-6">
                  <h3 className="font-semibold mb-3">Capabilities</h3>
                  <ul className="space-y-2 text-sm text-gray-700">
                    <li>• Crop recommendations</li>
                    <li>• Soil health guidance</li>
                    <li>• Weather analysis</li>
                    <li>• Pest management</li>
                    <li>• Irrigation planning</li>
                  </ul>
                </div>

                <div>
                  <h3 className="font-semibold mb-3">Quick Tips</h3>
                  <p className="text-sm text-gray-600">
                    Ask specific questions about your farm conditions for better recommendations.
                  </p>
                </div>
              </div>
            </div>

            {/* Chat Interface */}
            <div className="lg:col-span-2">
              <div className="bg-white rounded-lg border border-gray-200 flex flex-col h-[600px]">
                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4">
                  {messages.map((msg, idx) => (
                    <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                      <div
                        className={`max-w-[80%] rounded-lg px-4 py-3 ${msg.role === "user" ? "bg-emerald-600 text-white" : "bg-gray-100 text-gray-900 border border-gray-200"
                          }`}
                      >
                        <p className="text-sm">{msg.content}</p>
                        <p className={`text-xs mt-2 ${msg.role === "user" ? "text-emerald-100" : "text-gray-500"}`}>
                          {msg.timestamp}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Input */}
                <div className="border-t border-gray-200 p-4">
                  <div className="flex gap-3">
                    <input
                      type="text"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyPress={(e) => e.key === "Enter" && handleSend()}
                      placeholder="Ask FarmBot a question..."
                      className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                    />
                    <button
                      onClick={handleSend}
                      className="px-6 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors flex items-center gap-2"
                    >
                      <Send className="w-4 h-4" />
                      Send
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  )
}
