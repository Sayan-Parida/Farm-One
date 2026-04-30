"use client"

interface ResultsCardProps {
  data: any
  loading: boolean
  error: string | null
  onGetInsights: () => void
}

export default function ResultsCard({ data, loading, error, onGetInsights }: ResultsCardProps) {
  if (!data) return null

  return (
    <div className="border border-black rounded-sm p-6 md:p-8 max-w-2xl">
      <h2 className="text-lg font-serif font-bold mb-6">Location Details</h2>

      {error && <div className="text-red-600 text-sm mb-4">{error}</div>}

      <div className="space-y-4 mb-8">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs font-medium text-gray-600 mb-1">Latitude</p>
            <p className="font-mono text-sm">{data.location.lat.toFixed(4)}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-600 mb-1">Longitude</p>
            <p className="font-mono text-sm">{data.location.lon.toFixed(4)}</p>
          </div>
        </div>

        <div className="border-t border-black pt-4">
          <h3 className="font-medium text-sm mb-3">Weather</h3>
          {loading ? (
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin-custom" />
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div>
                <p className="text-xs text-gray-600 mb-1">Min Temp</p>
                <p>{data.weather.tmin_c}°C</p>
              </div>
              <div>
                <p className="text-xs text-gray-600 mb-1">Max Temp</p>
                <p>{data.weather.tmax_c}°C</p>
              </div>
              <div>
                <p className="text-xs text-gray-600 mb-1">7d Rain</p>
                <p>{data.weather.rain_7d_mm}mm</p>
              </div>
              <div>
                <p className="text-xs text-gray-600 mb-1">Humidity</p>
                <p>{data.weather.humidity_pct}%</p>
              </div>
            </div>
          )}
        </div>

        <div className="border-t border-black pt-4">
          <h3 className="font-medium text-sm mb-3">Soil</h3>
          {loading ? (
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin-custom" />
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div>
                <p className="text-xs text-gray-600 mb-1">pH (0–20cm)</p>
                <p>{data.soil.ph}</p>
              </div>
              <div>
                <p className="text-xs text-gray-600 mb-1">Organic Carbon</p>
                <p>{data.soil.oc_pct}%</p>
              </div>
              <div>
                <p className="text-xs text-gray-600 mb-1">Texture</p>
                <p>{data.soil.texture}</p>
              </div>
            </div>
          )}
        </div>

        <div className="border-t border-black pt-4">
          <p className="text-xs text-gray-600">
            Data via {data.source.weather} &amp; {data.source.soil}
          </p>
        </div>
      </div>

      <button
        onClick={onGetInsights}
        className="w-full px-4 py-3 border border-black bg-white text-black font-medium text-sm transition-colors hover:bg-black hover:text-white"
      >
        Get More Insights
      </button>
    </div>
  )
}
