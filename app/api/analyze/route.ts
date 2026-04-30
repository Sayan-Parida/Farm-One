export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const lat = searchParams.get("lat")
  const lon = searchParams.get("lon")

  if (!lat || !lon) {
    return new Response(JSON.stringify({ error: "Missing lat or lon" }), { status: 400 })
  }

  try {
    const backendUrl = process.env.NEXT_PUBLIC_API_BASE
    
    if (!backendUrl) {
      console.error("[v0] NEXT_PUBLIC_API_BASE not configured")
      return new Response(
        JSON.stringify({ 
          error: "Backend API not configured. Please set NEXT_PUBLIC_API_BASE in environment variables.",
          hint: "Add your backend URL (e.g., http://localhost:8000 or https://your-api.com) to the Vars section"
        }), 
        { status: 503 }
      )
    }

    console.log(`[v0] Fetching from backend: ${backendUrl}/api/analyze?lat=${lat}&lon=${lon}`)
    
    const response = await fetch(`${backendUrl}/api/analyze?lat=${lat}&lon=${lon}`, {
      headers: {
        "Content-Type": "application/json",
      },
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error(`[v0] Backend error ${response.status}:`, errorText)
      throw new Error(`Backend error: ${response.status} - ${errorText}`)
    }

    const data = await response.json()
    return new Response(JSON.stringify(data), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    })
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error)
    console.error("[v0] Backend fetch error:", errorMessage)
    return new Response(JSON.stringify({ error: "Failed to fetch from backend", details: errorMessage }), { status: 500 })
  }
}
