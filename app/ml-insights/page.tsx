"use client"

import { useState, useEffect } from "react"
import Navbar from "@/components/navbar"
import Footer from "@/components/footer"
import { Sprout, TrendingUp, MessageSquare, RefreshCw, Loader2 } from "lucide-react"

type MLFeature = "crop" | "yield" | "advisory"

interface CropRecommendation {
  crop: string
  expected_yield_t_ha: number
  range_t_ha: [number, number]
  relative_to_national_pct: number
  district_area_share_pct: number
  confidence_level: string
}

interface WeatherBasis {
  months_in_season: number
  months_observed: number
  season_rain_mm: number
  season_mean_temp_c: number
  rain_vs_normal_pct: number | null
  source: string
}

interface CropMeta {
  district: string
  state: string
  season: string
  agricultural_year: string
  method: string
  weather_basis: WeatherBasis
}

interface YieldPrediction {
  expected_yield_ton_per_hectare: number
  range_ton_per_hectare: [number, number]
  range_level: string
  confidence: string
  note: string
  crop: string
  season: string
  agricultural_year: string
  district: string
  state: string
  history: { years: string; mean_yield_t_ha: number; yearly: { year: string; yield_t_ha: number }[] }
  weather_basis: WeatherBasis
  available_crops: { crop: string; avg_area_ha: number }[]
  available_seasons: string[]
  model_accuracy: { tested_on: string; crop_median_error_pct: number | null; overall_median_error_pct: number }
}

const SEASONS = ["Kharif", "Rabi", "Summer", "Autumn", "Winter", "Whole Year"]

// Backend returns {error, ...} with a 4xx/5xx status when it can't give a reliable answer.
async function readError(response: Response) {
  try {
    const body = await response.json()
    return { message: body.error || `HTTP error! status: ${response.status}`, body }
  } catch {
    return { message: `HTTP error! status: ${response.status}`, body: null }
  }
}

export default function MLInsights() {
  const [activeFeature, setActiveFeature] = useState<MLFeature>("crop")
  const [soilPH, setSoilPH] = useState("")
  const [organicCarbon, setOrganicCarbon] = useState("")
  const [soilTexture, setSoilTexture] = useState("Loam")
  const [cropSeason, setCropSeason] = useState("")    // "" = current season (backend decides)
  const [yieldSeason, setYieldSeason] = useState("")
  const [yieldCrop, setYieldCrop] = useState("")        // "" = district's main crop
  const [yieldCropOptions, setYieldCropOptions] = useState<{ crop: string; avg_area_ha: number }[]>([])
  const [yieldSeasonOptions, setYieldSeasonOptions] = useState<string[]>([])
  const [cropMeta, setCropMeta] = useState<CropMeta | null>(null)
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
      const currentCrops = {
        recommended_crops: recommendations.map(r => ({
          crop: r.crop,
          expected_yield_t_ha: r.expected_yield_t_ha,
          relative_to_national_pct: r.relative_to_national_pct,
        }))
      }

      const currentYield = yieldResult ? {
        expected_yield_ton_per_hectare: yieldResult.expected_yield_ton_per_hectare,
        confidence: yieldResult.confidence,
        crop: yieldResult.crop,
        season: `${yieldResult.season} ${yieldResult.agricultural_year}`,
        district: `${yieldResult.district}, ${yieldResult.state}`,
      } : { expected_yield_ton_per_hectare: null, confidence: "N/A" }

      // Only real measurements; missing values are sent as null (the advisor shows N/A).
      const w = farmData.weather || {}
      const hasTemps = w.tmin_c != null && w.tmax_c != null
      const requestBody = {
        weather: {
          temperature: hasTemps ? (w.tmin_c + w.tmax_c) / 2 : null,
          temp_min: w.tmin_c ?? null,
          temp_max: w.tmax_c ?? null,
          humidity: w.humidity_pct ?? null,
          rainfall: w.rain_7d_mm ?? null,
          rain_7d: w.rain_7d_mm ?? null
        },
        soil: {
          ph: farmData.soil?.ph ?? null,
          organic_carbon_pct: farmData.soil?.oc_pct ?? null,
          texture: farmData.soil?.texture ?? null
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
            setSoilTexture(data.soil.texture || "N/A")
          }

          if (data.weather) {
            setRainfall(data.weather.rain_7d_mm?.toString() || "")
            // Use average of min and max temperature
            const { tmin_c, tmax_c } = data.weather
            setTemperature(tmin_c != null && tmax_c != null ? ((tmin_c + tmax_c) / 2).toFixed(1) : "")
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
  }, [activeFeature, farmDataVersion, cropSeason, yieldSeason, yieldCrop])

  const fetchYieldPrediction = async (farmData: any) => {
    setLoading(true)
    setError(null)

    try {
      if (farmData.location?.lat == null || farmData.location?.lon == null) {
        throw new Error("Select a location on the map first.")
      }
      const requestBody = {
        lat: farmData.location.lat,
        lon: farmData.location.lon,
        crop_name: yieldCrop || null,
        season: yieldSeason || null,
      }

      const response = await fetch(`/api/ml/yield`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody)
      })

      if (!response.ok) {
        const { message, body } = await readError(response)
        if (body?.available_crops) setYieldCropOptions(body.available_crops)
        if (body?.available_seasons) setYieldSeasonOptions(body.available_seasons)
        setYieldResult(null)
        throw new Error(message)
      }

      const data: YieldPrediction = await response.json()
      setYieldResult(data)
      setYieldCropOptions(data.available_crops || [])
      setYieldSeasonOptions(data.available_seasons || [])
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
      if (farmData.location?.lat == null || farmData.location?.lon == null) {
        throw new Error("Select a location on the map first.")
      }
      const requestBody = {
        lat: farmData.location.lat,
        lon: farmData.location.lon,
        season: cropSeason || null,
      }

      const response = await fetch(`/api/ml/crop`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody)
      })

      if (!response.ok) {
        const { message } = await readError(response)
        setRecommendations([])
        setCropMeta(null)
        throw new Error(message)
      }

      const data = await response.json()
      setRecommendations(data.recommended_crops || [])
      setCropMeta({
        district: data.district,
        state: data.state,
        season: data.season,
        agricultural_year: data.agricultural_year,
        method: data.method,
        weather_basis: data.weather_basis,
      })
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

                    <div className="flex flex-wrap items-center gap-3 mb-6 text-sm">
                      <label className="text-gray-600">Season</label>
                      <select value={cropSeason} onChange={(e) => setCropSeason(e.target.value)} className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-emerald-500 outline-none">
                        <option value="">Current season</option>
                        {SEASONS.map((s) => <option key={s} value={s}>{s}</option>)}
                      </select>
                      {cropMeta && (
                        <span className="text-gray-600">
                          {cropMeta.district}, {cropMeta.state} · {cropMeta.season} {cropMeta.agricultural_year}
                        </span>
                      )}
                    </div>

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
                                <h4 className="font-semibold text-lg">{rec.crop}</h4>
                                <p className="text-sm text-gray-600">
                                  Expected {rec.expected_yield_t_ha} t/ha (range {rec.range_t_ha[0]}–{rec.range_t_ha[1]})
                                  {" · "}{rec.relative_to_national_pct}% of India median
                                </p>
                                <p className="text-xs text-gray-500">
                                  {rec.district_area_share_pct}% of this season's recorded crop area in the district
                                </p>
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

                    {!loading && !error && recommendations.length > 0 && cropMeta && (
                      <p className="mt-6 text-xs text-gray-500 leading-relaxed">
                        {cropMeta.method} Weather: {cropMeta.weather_basis.months_observed} of{" "}
                        {cropMeta.weather_basis.months_in_season} season months observed, rest from district normals.
                        Soil readings are shown for reference only and are not used in this ranking.
                      </p>
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
                    <div className="flex flex-wrap items-center gap-3 text-sm">
                      <label className="text-gray-600">Crop</label>
                      <select value={yieldCrop} onChange={(e) => setYieldCrop(e.target.value)} className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-emerald-500 outline-none">
                        <option value="">District&apos;s main crop</option>
                        {yieldCropOptions.map((c) => (
                          <option key={c.crop} value={c.crop}>{c.crop}</option>
                        ))}
                      </select>
                      <label className="text-gray-600 ml-2">Season</label>
                      <select value={yieldSeason} onChange={(e) => { setYieldSeason(e.target.value); setYieldCrop("") }} className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-emerald-500 outline-none">
                        <option value="">Current season</option>
                        {(yieldSeasonOptions.length ? yieldSeasonOptions : SEASONS).map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </div>
                    <p className="mt-3 text-xs text-gray-500">
                      Crops listed are those with official production records in this district for the season.
                    </p>
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
                            <div className="text-sm uppercase tracking-wide text-emerald-800 mb-1 font-medium">
                              {yieldResult.crop} · {yieldResult.season} {yieldResult.agricultural_year}
                            </div>
                            <div className="text-4xl md:text-5xl font-serif font-bold text-emerald-900">
                              {yieldResult.expected_yield_ton_per_hectare} <span className="text-xl md:text-2xl font-sans font-normal text-emerald-700">tons/ha</span>
                            </div>
                            <div className="mt-1 text-sm text-emerald-800">
                              Likely range {yieldResult.range_ton_per_hectare[0]}–{yieldResult.range_ton_per_hectare[1]} t/ha
                            </div>
                          </div>

                          <div className="flex flex-col items-start md:items-end">
                            <span className={`px-4 py-2 rounded-full text-sm font-semibold border ${getConfidenceBadgeColor(yieldResult.confidence)}`}>
                              {yieldResult.confidence} Confidence
                            </span>
                            <div className="mt-2 text-sm text-gray-500">
                              District average · {yieldResult.district}, {yieldResult.state}
                            </div>
                          </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                            <h4 className="text-sm font-semibold text-gray-900 mb-2">
                              Official district yields ({yieldResult.history.years})
                            </h4>
                            <ul className="text-sm text-gray-600 space-y-1">
                              {yieldResult.history.yearly.map((h) => (
                                <li key={h.year} className="flex justify-between">
                                  <span>{h.year}</span><span>{h.yield_t_ha} t/ha</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                          <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                            <h4 className="text-sm font-semibold text-gray-900 mb-2">Season weather used</h4>
                            <ul className="text-sm text-gray-600 space-y-1">
                              <li className="flex justify-between"><span>Season rainfall</span><span>{yieldResult.weather_basis.season_rain_mm} mm</span></li>
                              <li className="flex justify-between">
                                <span>vs district normal</span>
                                <span>{yieldResult.weather_basis.rain_vs_normal_pct == null ? "normal assumed" : `${yieldResult.weather_basis.rain_vs_normal_pct > 0 ? "+" : ""}${yieldResult.weather_basis.rain_vs_normal_pct}%`}</span>
                              </li>
                              <li className="flex justify-between"><span>Mean temperature</span><span>{yieldResult.weather_basis.season_mean_temp_c} °C</span></li>
                              <li className="flex justify-between">
                                <span>Months observed</span>
                                <span>{yieldResult.weather_basis.months_observed} of {yieldResult.weather_basis.months_in_season}</span>
                              </li>
                            </ul>
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
                              <p className="mt-2 text-xs text-gray-500">
                                Model accuracy on unseen years {yieldResult.model_accuracy.tested_on}: median error{" "}
                                {yieldResult.model_accuracy.crop_median_error_pct ?? yieldResult.model_accuracy.overall_median_error_pct}%
                                {yieldResult.model_accuracy.crop_median_error_pct != null ? ` for ${yieldResult.crop}` : " overall"}.
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
                      <p><strong>Context Loaded:</strong> We've prepared your location's weather ({temperature || "N/A"}°C, {rainfall || "N/A"} mm in the last 7 days), soil parameters (pH {soilPH || "N/A"}), and crop analysis data for the AI.</p>
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
                        <span>AI-generated advice — verify important decisions with your local agriculture extension office.</span>
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
