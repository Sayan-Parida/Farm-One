"use client"

import { useEffect, useRef, useState } from "react"
import dynamic from "next/dynamic"

// Dynamically import Leaflet to avoid SSR issues
const L = typeof window !== "undefined" ? require("leaflet") : null

interface MapViewProps {
  onMapClick: (lat: number, lon: number) => void
  onDataFetched?: (data: any) => void
}

function MapViewComponent({ onMapClick, onDataFetched }: MapViewProps) {
  const mapRef = useRef<any>(null)
  const markerRef = useRef<any>(null)
  const popupRef = useRef<any>(null)
  const [analysisData, setAnalysisData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchAnalysisData = async (lat: number, lon: number) => {
    setLoading(true)
    setError(null)
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8001"
      const response = await fetch(`${apiBase}/api/analyze?lat=${lat}&lon=${lon}`)

      if (!response.ok) {
        let backendError: any = null
        try {
          backendError = await response.json()
        } catch {
          backendError = null
        }

        if (backendError?.code === "WATER_POINT") {
          const waterData = {
            isWater: true,
            message: "Please click on land.",
            location: { lat, lon },
          }
          setAnalysisData(waterData)
          // Don't treat water as a generic error so the water-specific
          // message is shown instead of the mock-data error banner.
          setError(null)

          if (typeof window !== "undefined") {
            sessionStorage.removeItem("farmData")
          }

          return waterData
        }

        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data = await response.json()
      setAnalysisData(data)

      // Store in sessionStorage for ML Insights page
      if (typeof window !== "undefined") {
        sessionStorage.setItem("farmData", JSON.stringify(data))
        // Notify other components that farmData has been updated
        console.log("🗺️ Map: Dispatching farmDataUpdated event with data:", data)
        window.dispatchEvent(new Event('farmDataUpdated'))
      }

      // Notify parent
      if (onDataFetched) {
        onDataFetched(data)
      }

      return data
    } catch (err: any) {
      console.error("Fetch Error:", err)
      setError("Error loading data: " + (err.message || "Unknown error"))
      const mockData = {
        location: { lat, lon },
        weather: { tmin_c: 21.4, tmax_c: 30.2, rain_7d_mm: 18, humidity_pct: 72 },
        soil: { ph: 6.5, oc_pct: 0.9, texture: "loam" },
        source: { weather: "Open-Meteo", soil: "SoilGrids" },
      }
      setAnalysisData(mockData)

      // Store mock data too
      if (typeof window !== "undefined") {
        sessionStorage.setItem("farmData", JSON.stringify(mockData))
        // Notify other components that farmData has been updated
        window.dispatchEvent(new Event('farmDataUpdated'))
      }

      return mockData
    } finally {
      setLoading(false)
    }
  }

  const createPopupContent = (data: any, isLoading: boolean, hasError: boolean) => {
    if (isLoading) {
      return `<div style="font-family: 'Inter', sans-serif; padding: 12px; width: 220px; color: #000;">Fetching data...</div>`
    }

    if (hasError) {
      return `<div style="font-family: 'Inter', sans-serif; padding: 12px; width: 220px; color: #dc2626;">Connection Failed - Using Mock Data</div>`
    }

    if (!data) return ""

    if (data.isWater) {
      return `
        <div style="font-family: 'Inter', sans-serif; padding: 12px; width: 240px; color: #000;">
          <h3 style="font-family: 'DM Serif Display', serif; font-size: 14px; font-weight: 600; margin: 0 0 8px 0; color: #000;">Location</h3>
          <p style="margin: 0 0 8px 0; font-size: 12px; line-height: 1.4;">Lat: ${data.location.lat.toFixed(4)}, Lon: ${data.location.lon.toFixed(4)}</p>
          <div style="padding: 10px; border: 1px solid #fecaca; background: #fef2f2; color: #b91c1c; border-radius: 6px; font-size: 12px; line-height: 1.4;">
            ${data.message}
          </div>
        </div>
      `
    }

    return `
      <div style="font-family: 'Inter', sans-serif; padding: 0; width: 240px; color: #000;">
        <div style="padding: 12px;">
          <h3 style="font-family: 'DM Serif Display', serif; font-size: 14px; font-weight: 600; margin: 0 0 8px 0; color: #000;">Location</h3>
          <p style="margin: 0 0 8px 0; font-size: 12px; line-height: 1.4;">Lat: ${data.location.lat.toFixed(4)}, Lon: ${data.location.lon.toFixed(4)}</p>
          
          <h3 style="font-family: 'DM Serif Display', serif; font-size: 14px; font-weight: 600; margin: 8px 0 6px 0; color: #000;">Weather</h3>
          <p style="margin: 0 0 4px 0; font-size: 12px;">Min: ${data.weather.tmin_c}°C  Max: ${data.weather.tmax_c}°C</p>
          <p style="margin: 0 0 6px 0; font-size: 12px;">Rain (7d): ${data.weather.rain_7d_mm}mm  Humidity: ${data.weather.humidity_pct}%</p>
          
          <h3 style="font-family: 'DM Serif Display', serif; font-size: 14px; font-weight: 600; margin: 8px 0 6px 0; color: #000;">Soil</h3>
          <p style="margin: 0 0 4px 0; font-size: 12px;">pH: ${data.soil.ph}  OC: ${data.soil.oc_pct}%  Texture: ${data.soil.texture}</p>
          
          <button id="insights-btn" style="margin-top: 8px; width: 100%; padding: 8px 12px; border: 1px solid #000; background: #fff; color: #000; font-size: 12px; font-weight: 500; cursor: pointer; border-radius: 4px; font-family: 'Inter', sans-serif; transition: all 0.2s;">More Insights</button>
        </div>
      </div>
    `
  }

  useEffect(() => {
    if (popupRef.current && markerRef.current) {
      const content = createPopupContent(analysisData, loading, !!error)
      popupRef.current.setContent(content)

      if (typeof window !== "undefined") {
        setTimeout(() => {
          const insightsBtn = document.getElementById("insights-btn")
          if (insightsBtn && analysisData) {
            insightsBtn.addEventListener("click", () => {
              // Navigate to ML Insights page
              window.location.href = "/ml-insights"
            })
          }
        }, 0)
      }
    }
  }, [analysisData, loading, error])

  useEffect(() => {
    if (!L || mapRef.current) return

    const map = L.map("map").setView([20, 0], 3)

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap contributors",
      maxZoom: 19,
    }).addTo(map)

    map.on("click", async (e: any) => {
      const { lat, lng } = e.latlng

      // Remove old marker and popup
      if (markerRef.current) {
        map.removeLayer(markerRef.current)
      }
      if (popupRef.current) {
        map.closePopup(popupRef.current)
      }

      const popup = L.popup({
        className: "custom-popup",
        maxWidth: 280,
        minWidth: 240,
        closeButton: true,
      }).setContent(createPopupContent(null, true, false))

      markerRef.current = L.marker([lat, lng], {
        icon: L.icon({
          iconUrl:
            'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="black" width="32" height="32"%3E%3Cpath d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8z"/%3E%3C/svg%3E',
          iconSize: [32, 32],
          iconAnchor: [16, 32],
          popupAnchor: [0, -32],
        }),
      })
        .addTo(map)
        .bindPopup(popup)
        .openPopup()

      popupRef.current = popup

      map.setView([lat, lng], map.getZoom())

      // Call parent callback
      onMapClick(lat, lng)

      // Fetch data after popup is shown
      await fetchAnalysisData(lat, lng)
    })

    mapRef.current = map
  }, [onMapClick])

  return (
    <div className="w-full border border-gray-200 rounded-lg overflow-hidden">
      <div id="map" style={{ height: "500px", width: "100%" }} />
      <style jsx>{`
        :global(.custom-popup .leaflet-popup-content-wrapper) {
          background: white;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
          padding: 0 !important;
        }
        :global(.custom-popup .leaflet-popup-content) {
          margin: 0 !important;
          padding: 0 !important;
        }
        :global(.custom-popup .leaflet-popup-tip) {
          background: white;
          border: 1px solid #e5e7eb;
        }
        :global(.custom-popup button:hover) {
          background: black !important;
          color: white !important;
        }
      `}</style>
    </div>
  )
}

// Export with SSR disabled
export default dynamic(() => Promise.resolve(MapViewComponent), {
  ssr: false,
})
