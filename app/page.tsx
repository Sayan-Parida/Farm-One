"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Navbar from "@/components/navbar"
import MapView from "@/components/map-view"
import Footer from "@/components/footer"
import { MapPin, TrendingUp, Leaf } from "lucide-react"

export default function Home() {
  const router = useRouter()

  return (
    <div className="min-h-screen bg-gradient-to-b from-emerald-50/30 to-white flex flex-col">
      <Navbar />

      <main className="flex-1">
        {/* Hero Section */}
        <section className="w-full max-w-6xl mx-auto px-4 md:px-8 py-16 md:py-24 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-100 text-emerald-700 text-sm font-medium mb-8">
            <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
            AI-Powered Agriculture
          </div>

          <h1 className="text-4xl md:text-6xl font-serif font-bold mb-6">
            Revolutionizing
            <br />
            <span className="text-emerald-600">Smart Farming</span>
          </h1>

          <p className="text-lg md:text-xl text-gray-600 max-w-3xl mx-auto mb-10">
            FarmOne combines advanced satellite imagery with machine learning to provide real-time crop insights, soil
            analysis, and yield predictions for smarter agricultural decisions.
          </p>


        </section>

        {/* Feature Cards */}
        <section className="w-full max-w-6xl mx-auto px-4 md:px-8 py-12">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Satellite Intelligence */}
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-emerald-100 flex items-center justify-center">
                <MapPin className="w-8 h-8 text-emerald-600" />
              </div>
              <h3 className="text-xl font-serif font-bold mb-3">Satellite Intelligence</h3>
              <p className="text-gray-600 text-sm leading-relaxed">
                High-resolution mapping and satellite data analysis for precise field monitoring.
              </p>
            </div>

            {/* Yield Prediction */}
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-emerald-100 flex items-center justify-center">
                <TrendingUp className="w-8 h-8 text-emerald-600" />
              </div>
              <h3 className="text-xl font-serif font-bold mb-3">Yield Prediction</h3>
              <p className="text-gray-600 text-sm leading-relaxed">
                AI-driven algorithms to forecast crop yields and optimize harvest planning.
              </p>
            </div>

            {/* Soil Health */}
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-emerald-100 flex items-center justify-center">
                <Leaf className="w-8 h-8 text-emerald-600" />
              </div>
              <h3 className="text-xl font-serif font-bold mb-3">Soil Health</h3>
              <p className="text-gray-600 text-sm leading-relaxed">
                Comprehensive soil analysis to maintain optimal growing conditions year-round.
              </p>
            </div>
          </div>
        </section>

        {/* Map Section */}
        <section className="w-full max-w-6xl mx-auto px-4 md:px-8 py-16">
          <h2 className="text-3xl font-serif font-bold text-center mb-4">Choose a map location to begin</h2>
          <p className="text-center text-gray-600 mb-8">
            Click anywhere on the map to fetch real-time weather and soil data
          </p>

          {/* Map */}
          <div className="w-full">
            <MapView onMapClick={(lat, lon) => {
              console.log("Map clicked:", lat, lon)
            }} />
          </div>
        </section>
      </main>

      <Footer />
    </div>
  )
}
