"use client"

import { useState } from "react"

interface StartPanelProps {
  onUseMap: (lat: number, lon: number, crop?: string) => void
}

export default function StartPanel({ onUseMap }: StartPanelProps) {
  const [lat, setLat] = useState("")
  const [lon, setLon] = useState("")

  const handleUseMap = () => {
    if (lat && lon) {
      onUseMap(Number.parseFloat(lat), Number.parseFloat(lon))
    }
  }

  return (
    <section className="w-full bg-white border-b border-black py-12 md:py-16">
      <div className="max-w-3xl mx-auto px-4 md:px-8">
        <h1 className="text-center text-2xl md:text-3xl font-serif font-bold mb-8">Choose a map location to begin</h1>

        <div className="space-y-4 md:flex md:gap-4 md:items-end md:space-y-0">
          <div className="flex-1">
            <label className="block text-sm font-medium mb-2">Latitude</label>
            <input
              type="number"
              step="0.0001"
              value={lat}
              onChange={(e) => setLat(e.target.value)}
              placeholder="e.g., 22.57"
              className="w-full px-3 py-2 border border-black bg-white text-black placeholder-gray-600 text-sm focus:outline-black"
            />
          </div>

          <div className="flex-1">
            <label className="block text-sm font-medium mb-2">Longitude</label>
            <input
              type="number"
              step="0.0001"
              value={lon}
              onChange={(e) => setLon(e.target.value)}
              placeholder="e.g., 88.36"
              className="w-full px-3 py-2 border border-black bg-white text-black placeholder-gray-600 text-sm focus:outline-black"
            />
          </div>

          <button
            onClick={handleUseMap}
            disabled={!lat || !lon}
            className="md:flex-shrink-0 w-full md:w-auto px-6 py-2 border border-black bg-white text-black font-medium text-sm transition-colors hover:bg-black hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Use Map
          </button>
        </div>
      </div>
    </section>
  )
}
