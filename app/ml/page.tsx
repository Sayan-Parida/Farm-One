"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Navbar from "@/components/navbar"
import Footer from "@/components/footer"
import Link from "next/link"

type ModelType = "knn" | "random-forest" | "logistic-regression" | "kmeans" | "linear-regression"

export default function MLPage() {
  const router = useRouter()
  const [location, setLocation] = useState<{ lat: number; lon: number } | null>(null)
  const [activeModel, setActiveModel] = useState<ModelType>("knn")

  useEffect(() => {
    // Retrieve location from sessionStorage
    const storedLocation = sessionStorage.getItem("mlLocation")
    if (storedLocation) {
      try {
        const parsedLocation = JSON.parse(storedLocation)
        setLocation(parsedLocation)
      } catch {
        // If parsing fails, location remains null
      }
    }
  }, [])

  const models = [
    { id: "knn" as ModelType, label: "Similar Region Crops (k-NN)" },
    { id: "random-forest" as ModelType, label: "Crop Suitability (Random Forest)" },
    { id: "logistic-regression" as ModelType, label: "Baseline Suitability (Logistic Regression)" },
    { id: "kmeans" as ModelType, label: "Agro-Climatic Zone (K-Means)" },
    { id: "linear-regression" as ModelType, label: "Yield Estimation (Linear Regression)" },
  ]

  const renderModelOutput = () => {
    if (!location) {
      return (
        <div className="p-8 text-center">
          <p className="text-gray-700 mb-4">Please select a location on the map first.</p>
          <Link href="/" className="text-blue-600 hover:underline">
            Go back to map
          </Link>
        </div>
      )
    }

    switch (activeModel) {
      case "knn":
        return (
          <div className="p-8">
            <h3 className="font-serif font-bold text-lg mb-4">Recommended Crops</h3>
            <div className="space-y-2">
              <p className="text-gray-800">Wheat (0.81)</p>
              <p className="text-gray-800">Mustard (0.74)</p>
              <p className="text-gray-800">Chickpea (0.69)</p>
            </div>
          </div>
        )

      case "random-forest":
        return (
          <div className="p-8">
            <h3 className="font-serif font-bold text-lg mb-4">Crop Suitability</h3>
            <p className="text-gray-800 mb-2">Crop: Wheat</p>
            <p className="text-gray-800">Suitability Score: 78%</p>
          </div>
        )

      case "logistic-regression":
        return (
          <div className="p-8">
            <h3 className="font-serif font-bold text-lg mb-4">Baseline Probability</h3>
            <p className="text-gray-800">Baseline Probability: 0.73</p>
          </div>
        )

      case "kmeans":
        return (
          <div className="p-8">
            <h3 className="font-serif font-bold text-lg mb-4">Agro-Climatic Zone</h3>
            <p className="text-gray-800 mb-2">Agro-Climatic Zone: Zone 3</p>
            <p className="text-gray-800">Common Crops: Wheat, Pulses</p>
          </div>
        )

      case "linear-regression":
        return (
          <div className="p-8">
            <h3 className="font-serif font-bold text-lg mb-4">Estimated Yield</h3>
            <p className="text-gray-800">3.2 – 3.6 tons per hectare</p>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Navbar />

      <main className="flex-1">
        <div className="w-full max-w-6xl mx-auto px-4 md:px-8 py-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {/* Left Sidebar - Model Selector */}
            <div className="md:col-span-1">
              <h2 className="font-serif font-bold text-lg mb-6">ML Models</h2>
              <div className="space-y-3">
                {models.map((model) => (
                  <button
                    key={model.id}
                    onClick={() => setActiveModel(model.id)}
                    className={`w-full text-left px-4 py-3 border text-sm font-medium transition-all ${
                      activeModel === model.id
                        ? "border-black bg-black text-white"
                        : "border-black bg-white text-black hover:bg-gray-50"
                    }`}
                  >
                    {model.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Right Panel - Model Output */}
            <div className="md:col-span-3 border border-black">
              <div className="border-b border-black p-8">
                <h3 className="font-serif font-bold text-base mb-4">Selected Location</h3>
                {location ? (
                  <div className="text-sm text-gray-800">
                    <p>Latitude: {location.lat.toFixed(4)}</p>
                    <p>Longitude: {location.lon.toFixed(4)}</p>
                  </div>
                ) : (
                  <p className="text-sm text-gray-700">No location selected</p>
                )}
              </div>

              <div>
                {renderModelOutput()}
              </div>
            </div>
          </div>

          {/* Back to Map Link */}
          <div className="mt-8">
            <Link href="/" className="text-sm font-medium text-blue-600 hover:underline">
              ← Back to Map
            </Link>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  )
}
