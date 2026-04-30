async function proxyToBackend(request: Request, path: string) {
  const backendUrl = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000"
  const targetUrl = `${backendUrl}${path}`
  const body = await request.text()

  const response = await fetch(targetUrl, {
    method: request.method,
    headers: {
      "Content-Type": request.headers.get("content-type") || "application/json",
    },
    body,
  })

  const responseText = await response.text()
  return new Response(responseText, {
    status: response.status,
    headers: { "Content-Type": response.headers.get("content-type") || "application/json" },
  })
}

export async function POST(request: Request) {
  return proxyToBackend(request, "/api/ml/chat")
}
