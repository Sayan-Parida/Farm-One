"use client"

import { useState, useEffect } from "react"
import Navbar from "@/components/navbar"
import Footer from "@/components/footer"
import { Sprout, TrendingUp, MessageSquare, RefreshCw, Loader2 } from "lucide-react"

type MLFeature = "crop" | "yield" | "advisory"

interface CropRecommendation {
  crop: string
  success_percentage: number
  confidence_level: string
}

interface YieldPrediction {
  expected_yield_ton_per_hectare: number
  confidence: string
  note: string
}

export default function MLInsights() {
  const [activeFeature, setActiveFeature] = useState<MLFeature>("crop")
  const [soilPH, setSoilPH] = useState("")
  const [organicCarbon, setOrganicCarbon] = useState("")
  const [soilTexture, setSoilTexture] = useState("Loam")
  const [season, setSeason] = useState("Kharif")
  const [rainfall, setRainfall] = useState("")
  const [temperature, setTemperature] = useState("")
  const [hasData, setHasData] = useState(false)
  const [loading, setLoading] = useState(false)
  const [recommendations, setRecommendations] = useState<CropRecommendation[]>([])
  const [error, setError] = useState<string | null>(null)
  const [advisoryQuestion, setAdvisoryQuestion] = useState("")
  const [advisoryResult, setAdvisoryResult] = useState<string | null>(null)
  const [yieldResult, setYieldResult] = useState<YieldPrediction | null>(null)

  const fetchAdvisory = async () => {
    setLoading(true)
    setError(null)

    try {
      // Get stored data
      const storedData = sessionStorage.getItem("farmData")
      const farmData = storedData ? JSON.parse(storedData) : {}

      // Get previous results if available
      const currentCrops = recommendations.length > 0 ? {
        recommended_crops: recommendations.map(r => ({ crop: r.crop, success_percentage: r.success_percentage }))
      } : { recommended_crops: [] }

      const currentYield = yieldResult ? {
        expected_yield_ton_per_hectare: yieldResult.expected_yield_ton_per_hectare,
        confidence: yieldResult.confidence
      } : { expected_yield_ton_per_hectare: 0, confidence: "N/A" }

      const requestBody = {
        weather: {
          temperature: (farmData.weather?.tmin_c + farmData.weather?.tmax_c) / 2 || 25,
          temp_min: farmData.weather?.tmin_c || 20,
          temp_max: farmData.weather?.tmax_c || 30,
          humidity: farmData.weather?.humidity_pct || 70,
          rainfall: farmData.weather?.rain_7d_mm || 50, // Using 7d rain as proxy
          rain_7d: farmData.weather?.rain_7d_mm || 50
        },
        soil: {
          ph: farmData.soil?.ph || 6.5,
          organic_carbon_pct: farmData.soil?.oc_pct || 0.5,
          texture: farmData.soil?.texture || "loam"
        },
        crop_recommendation: currentCrops,
        yield_prediction: currentYield,
        question: advisoryQuestion || "What crops are best for this area?"
      }

      const response = await fetch(`/api/ml/advice`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody)
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setAdvisoryResult(data.advisory)
    } catch (err: any) {
      console.error("Error fetching advisory:", err)
      setError(err.message || "Failed to fetch advisory")
    } finally {
      setLoading(false)
    }
  }

  // Add a state to track when farmData changes
  const [farmDataVersion, setFarmDataVersion] = useState(0)

  // Listen for storage changes (when map updates farmData)
  useEffect(() => {
    const handleStorageChange = () => {
      console.log("📊 ML Insights: Received farmDataUpdated event, incrementing version")
      setFarmDataVersion(prev => prev + 1)
    }


    console.log("📊 ML Insights: Registering farmDataUpdated event listener")
    // Listen for custom event from map
    window.addEventListener('farmDataUpdated', handleStorageChange)

    return () => {
      window.removeEventListener('farmDataUpdated', handleStorageChange)
    }
  }, [])

  useEffect(() => {
    console.log("📊 ML Insights: Data loading useEffect triggered. farmDataVersion:", farmDataVersion, "activeFeature:", activeFeature)
    // Load data from sessionStorage
    if (typeof window !== "undefined") {
      const storedData = sessionStorage.getItem("farmData")
      console.log("📊 ML Insights: Retrieved from sessionStorage:", storedData ? "Data found" : "No data")
      if (storedData) {
        try {
          const data = JSON.parse(storedData)
          console.log("📊 ML Insights: Parsed farm data:", data)

          // Auto-populate form fields
          if (data.soil) {
            setSoilPH(data.soil.ph?.toString() || "")
            setOrganicCarbon(data.soil.oc_pct?.toString() || "")
            setSoilTexture(data.soil.texture || "Loam")
          }

          if (data.weather) {
            setRainfall(data.weather.rain_7d_mm?.toString() || "")
            // Use average of min and max temperature
            const avgTemp = ((data.weather.tmin_c + data.weather.tmax_c) / 2).toFixed(1)
            setTemperature(avgTemp)
          }

          setHasData(true)

          // Automatically fetch recommendations for active feature
          if (activeFeature === "crop") {
            console.log("📊 ML Insights: Calling fetchCropRecommendations")
            fetchCropRecommendations(data)
          } else if (activeFeature === "yield") {
            console.log("📊 ML Insights: Calling fetchYieldPrediction")
            fetchYieldPrediction(data)
          }
        } catch (err) {
          console.error("Error parsing stored data:", err)
        }
      }
    }
  }, [activeFeature, farmDataVersion])

  const fetchYieldPrediction = async (farmData: any) => {
    setLoading(true)
    setError(null)

    try {
      const requestBody = {
        weather: {
          temp_min: farmData.weather?.tmin_c || 20,
          temp_max: farmData.weather?.tmax_c || 30,
          humidity: farmData.weather?.humidity_pct || 70,
          rain_7d: farmData.weather?.rain_7d_mm || 50
        },
        soil: {
          ph: farmData.soil?.ph || 6.5,
          organic_carbon_pct: farmData.soil?.oc_pct || 0.5
        }
      }

      const response = await fetch(`/api/ml/yield`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody)
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      setYieldResult(data)
    } catch (err: any) {
      console.error("Error fetching yield prediction:", err)
      setError(err.message || "Failed to fetch yield prediction")
    } finally {
      setLoading(false)
    }
  }

  const fetchCropRecommendations = async (farmData: any) => {
    setLoading(true)
    setError(null)

    try {
      // Prepare request body from farm data
      const tMin = Number(farmData.weather?.tmin_c)
      const tMax = Number(farmData.weather?.tmax_c)
      const avgTemp = (!isNaN(tMin) && !isNaN(tMax)) ? (tMin + tMax) / 2 : 25

      const requestBody = {
        weather: {
          temperature: avgTemp,
          humidity: Number(farmData.weather?.humidity_pct) || 70,
          rainfall: Number(farmData.weather?.rain_7d_mm) || 100
        },
        soil: {
          ph: Number(farmData.soil?.ph) || 6.5
        }
      }

      console.log("🌾 Frontend: Sending crop request:", requestBody)

      const response = await fetch(`/api/ml/crop`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody)
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      console.log("🌾 Frontend: Received crop response:", data)
      setRecommendations(data.recommended_crops || [])
    } catch (err: any) {
      console.error("Error fetching recommendations:", err)
      setError(err.message || "Failed to fetch crop recommendations")
    } finally {
      setLoading(false)
    }
  }

  const getConfidenceBadgeColor = (confidence: string) => {
    switch (confidence.toLowerCase()) {
      case "high":
        return "bg-emerald-100 text-emerald-700 border-emerald-200"
      case "medium":
        return "bg-yellow-100 text-yellow-700 border-yellow-200"
      case "low":
        return "bg-red-100 text-red-700 border-red-200"
      default:
        return "bg-gray-100 text-gray-700 border-gray-200"
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Navbar />

      <main className="flex-1">
        <div className="w-full max-w-7xl mx-auto px-4 md:px-8 py-12">
          {/* Page Header */}
          <div className="mb-12">
            <h1 className="text-4xl md:text-5xl font-serif font-bold mb-4">
              ML <span className="text-emerald-600">Insights</span>
            </h1>
            <p className="text-gray-600 text-lg">
              Harness the power of artificial intelligence to optimize your yield. Select a feature below to begin your
              analysis.
            </p>
            {!hasData && (
              <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-sm text-yellow-800">
                  ℹ️ No location data found. Please select a location on the{" "}
                  <a href="/" className="underline font-semibold">
                    home page map
                  </a>{" "}
                  first.
                </p>
              </div>
            )}
          </div>

          {/* Main Content Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            {/* Sidebar */}
            <div className="lg:col-span-1 space-y-3">
              {/* Crop Recommendation */}
              <button
                onClick={() => setActiveFeature("crop")}
                className={`w-full text-left px-6 py-4 rounded-lg transition-all ${activeFeature === "crop"
                  ? "bg-gray-900 text-white shadow-lg"
                  : "bg-white text-gray-700 hover:bg-gray-100 border border-gray-200"
                  }`}
              >
                <div className="flex items-center gap-3">
                  <Sprout className="w-5 h-5" />
                  <div>
                    <div className="font-semibold">Crop Recommendation</div>
                    <div className="text-xs opacity-80 mt-1">AI-powered crop suitability</div>
                  </div>
                </div>
              </button>

              {/* Yield Prediction */}
              <button
                onClick={() => setActiveFeature("yield")}
                className={`w-full text-left px-6 py-4 rounded-lg transition-all ${activeFeature === "yield"
                  ? "bg-gray-900 text-white shadow-lg"
                  : "bg-white text-gray-700 hover:bg-gray-100 border border-gray-200"
                  }`}
              >
                <div className="flex items-center gap-3">
                  <TrendingUp className="w-5 h-5" />
                  <div>
                    <div className="font-semibold">Yield Prediction</div>
                    <div className="text-xs opacity-80 mt-1">Estimate harvest output</div>
                  </div>
                </div>
              </button>

              {/* AI Advisory */}
              <button
                onClick={() => setActiveFeature("advisory")}
                className={`w-full text-left px-6 py-4 rounded-lg transition-all ${activeFeature === "advisory"
                  ? "bg-gray-900 text-white shadow-lg"
                  : "bg-white text-gray-700 hover:bg-gray-100 border border-gray-200"
                  }`}
              >
                <div className="flex items-center gap-3">
                  <MessageSquare className="w-5 h-5" />
                  <div>
                    <div className="font-semibold">AI Advisory</div>
                    <div className="text-xs opacity-80 mt-1">Expert farming guidance</div>
                  </div>
                </div>
              </button>
            </div>

            {/* Main Panel */}
            <div className="lg:col-span-3">
              {activeFeature === "crop" && (
                <div className="space-y-6">
                  {/* Input Data Card */}
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
                    {/* Header */}
                    <div className="flex items-center gap-3 mb-6">
                      <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center">
                        <RefreshCw className="w-6 h-6 text-emerald-600" />
                      </div>
                      <div>
                        <h2 className="text-2xl font-serif font-bold">Crop Suitability Predictor</h2>
                        <p className="text-sm text-gray-600">AI Recommendation Engine</p>
                      </div>
                    </div>

                    {hasData && (
                      <div className="mb-6 p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
                        <p className="text-sm text-emerald-800">
                          ✓ Data loaded from your selected location. Analysis running automatically.
                        </p>
                      </div>
                    )}

                    {/* Form - Display Only */}
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                      <div>
                        <div className="text-gray-500 uppercase tracking-wide text-xs mb-1">Soil PH</div>
                        <div className="font-semibold">{soilPH || "N/A"}</div>
                      </div>
                      <div>
                        <div className="text-gray-500 uppercase tracking-wide text-xs mb-1">Organic Carbon (%)</div>
                        <div className="font-semibold">{organicCarbon || "N/A"}</div>
                      </div>
                      <div>
                        <div className="text-gray-500 uppercase tracking-wide text-xs mb-1">Soil Texture</div>
                        <div className="font-semibold">{soilTexture}</div>
                      </div>

                      <div>
                        <div className="text-gray-500 uppercase tracking-wide text-xs mb-1">Rainfall (mm)</div>
                        <div className="font-semibold">{rainfall || "N/A"}</div>
                      </div>
                      <div>
                        <div className="text-gray-500 uppercase tracking-wide text-xs mb-1">Temperature (°C)</div>
                        <div className="font-semibold">{temperature || "N/A"}</div>
                      </div>
                    </div>
                  </div>

                  {/* Results Card */}
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
                    <h3 className="text-xl font-serif font-bold mb-6">Recommended Crops</h3>

                    {loading && (
                      <div className="flex items-center justify-center py-12">
                        <Loader2 className="w-8 h-8 text-emerald-600 animate-spin" />
                        <span className="ml-3 text-gray-600">Analyzing your farm data...</span>
                      </div>
                    )}

                    {error && (
                      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                        <p className="text-sm text-red-800">Error: {error}</p>
                      </div>
                    )}

                    {!loading && !error && recommendations.length > 0 && (
                      <div className="space-y-4">
                        {recommendations.map((rec, idx) => (
                          <div
                            key={idx}
                            className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:border-emerald-300 transition-colors"
                          >
                            <div className="flex items-center gap-4">
                              <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center">
                                <Sprout className="w-6 h-6 text-emerald-600" />
                              </div>
                              <div>
                                <h4 className="font-semibold text-lg capitalize">{rec.crop}</h4>
                                <p className="text-sm text-gray-600">Success Rate: {rec.success_percentage}%</p>
                              </div>
                            </div>
                            <div>
                              <span
                                className={`px-3 py-1 rounded-full text-xs font-medium border ${getConfidenceBadgeColor(
                                  rec.confidence_level
                                )}`}
                              >
                                {rec.confidence_level}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {!loading && !error && recommendations.length === 0 && hasData && (
                      <div className="text-center py-12 text-gray-500">
                        <p>No recommendations available. Please try selecting a different location.</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {activeFeature === "yield" && (
                <div className="space-y-6">
                  {/* Input Data Card (for Context) */}
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
                    <div className="flex items-center gap-3 mb-6">
                      <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center">
                        <TrendingUp className="w-6 h-6 text-emerald-600" />
                      </div>
                      <div>
                        <h2 className="text-2xl font-serif font-bold">Yield Prediction Engine</h2>
                        <p className="text-sm text-gray-600">AI-Powered Harvest Estimation</p>
                      </div>
                    </div>
                    {/* Form - Display Only Summary */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-2">
                      <div>
                        <div className="text-gray-500 uppercase tracking-wide text-xs mb-1">Temperature</div>
                        <div className="font-semibold">{temperature} °C</div>
                      </div>
                      <div>
                        <div className="text-gray-500 uppercase tracking-wide text-xs mb-1">Rainfall</div>
                        <div className="font-semibold">{rainfall} mm</div>
                      </div>
                      <div>
                        <div className="text-gray-500 uppercase tracking-wide text-xs mb-1">Soil PH</div>
                        <div className="font-semibold">{soilPH}</div>
                      </div>
                      <div>
                        <div className="text-gray-500 uppercase tracking-wide text-xs mb-1">Organic Carbon</div>
                        <div className="font-semibold">{organicCarbon}%</div>
                      </div>
                    </div>
                  </div>

                  {/* Results Card */}
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
                    <h3 className="text-xl font-serif font-bold mb-6">Prediction Results</h3>

                    {loading && (
                      <div className="flex items-center justify-center py-12">
                        <Loader2 className="w-8 h-8 text-emerald-600 animate-spin" />
                        <span className="ml-3 text-gray-600">Calculating potential yield...</span>
                      </div>
                    )}

                    {error && (
                      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                        <p className="text-sm text-red-800">Error: {error}</p>
                      </div>
                    )}

                    {!loading && !error && yieldResult && (
                      <div className="space-y-6">
                        <div className="flex flex-col md:flex-row gap-6 md:items-center justify-between p-6 bg-emerald-50 rounded-xl border border-emerald-100">
                          <div>
                            <div className="text-sm uppercase tracking-wide text-emerald-800 mb-1 font-medium">Expected Yield</div>
                            <div className="text-4xl md:text-5xl font-serif font-bold text-emerald-900">
                              {yieldResult.expected_yield_ton_per_hectare} <span className="text-xl md:text-2xl font-sans font-normal text-emerald-700">tons/ha</span>
                            </div>
                          </div>

                          <div className="flex flex-col items-start md:items-end">
                            <span className={`px-4 py-2 rounded-full text-sm font-semibold border ${getConfidenceBadgeColor(yieldResult.confidence)}`}>
                              {yieldResult.confidence} Confidence
                            </span>
                            <div className="mt-2 text-sm text-gray-500">Based on climate & soil analysis</div>
                          </div>
                        </div>

                        <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                          <div className="flex gap-3">
                            <div className="mt-1">
                              <MessageSquare className="w-4 h-4 text-gray-400" />
                            </div>
                            <div>
                              <h4 className="text-sm font-semibold text-gray-900 mb-1">Analysis Note</h4>
                              <p className="text-sm text-gray-600 leading-relaxed">
                                {yieldResult.note}
                              </p>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {!loading && !error && !yieldResult && hasData && (
                      <div className="text-center py-12 text-gray-500">
                        <p>Select the Yield Prediction tab to start analysis.</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {activeFeature === "advisory" && (
                <div className="space-y-6">
                  {/* Context Card */}
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
                    <div className="flex items-center gap-3 mb-6">
                      <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center">
                        <MessageSquare className="w-6 h-6 text-emerald-600" />
                      </div>
                      <div>
                        <h2 className="text-2xl font-serif font-bold">AI Expert Advisory</h2>
                        <p className="text-sm text-gray-600">Personalized farming guidance based on your data</p>
                      </div>
                    </div>

                    <div className="bg-emerald-50 border border-emerald-100 rounded-lg p-4 mb-6 text-sm text-gray-700">
                      <p><strong>Context Loaded:</strong> We've prepared your location's weather ({temperature}°C, {rainfall}mm), soil parameters (pH {soilPH}), and crop analysis data for the AI.</p>
                    </div>

                    <div className="space-y-4">
                      <label className="block text-sm font-medium text-gray-700">
                        Ask a specific question (Optional)
                      </label>
                      <div className="flex gap-4">
                        <input
                          type="text"
                          value={advisoryQuestion}
                          onChange={(e) => setAdvisoryQuestion(e.target.value)}
                          placeholder="E.g., Can I grow pigeonpeas in these conditions?"
                          className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
                        />
                        <button
                          onClick={() => fetchAdvisory()}
                          disabled={loading}
                          className="px-6 py-3 bg-gray-900 text-white font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                        >
                          {loading ? (
                            <>
                              <Loader2 className="w-4 h-4 animate-spin" />
                              Thinking...
                            </>
                          ) : (
                            <>
                              <MessageSquare className="w-4 h-4" />
                              Get Advice
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Results Card */}
                  {advisoryResult && (
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
                      <h3 className="text-xl font-serif font-bold mb-6">Expert Recommendations</h3>

                      <div className="prose prose-emerald max-w-none text-gray-700 leading-relaxed whitespace-pre-wrap">
                        {/* Simple rendering for markdown-like bolding */}
                        {advisoryResult.split("\n").map((line, i) => (
                          <p key={i} className="mb-4" dangerouslySetInnerHTML={{
                            __html: line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                          }} />
                        ))}
                      </div>

                      <div className="mt-8 pt-6 border-t border-gray-100 flex items-center justify-between text-sm text-gray-500">
                        <span>AI-generated advice based on real-time factors.</span>
                        <div className="flex gap-2">
                          <button onClick={() => setAdvisoryQuestion("")} className="text-emerald-600 hover:underline">Clear</button>
                        </div>
                      </div>
                    </div>
                  )}

                  {error && (
                    <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                      <p className="text-sm text-red-800">Error: {error}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  )
}
