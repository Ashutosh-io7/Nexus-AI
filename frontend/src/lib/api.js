const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export async function getHealth() {
  const response = await fetch(`${API_BASE_URL}/health`)
  // /health answers with status 503 when the database is down,
  // but the body still tells us what is wrong.
  return response.json()
}

// The backend reports problems as { "detail": "message" }.
async function readErrorMessage(response) {
  try {
    const body = await response.json()
    if (typeof body.detail === 'string') return body.detail
  } catch {
    // The body was not JSON, so use the generic message below.
  }
  return `Request failed (status ${response.status}).`
}

export async function previewCustomersCsv(file) {
  const formData = new FormData()
  formData.append('file', file)

  let response
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/customers/upload-preview`, {
      method: 'POST',
      body: formData,
    })
  } catch {
    throw new Error(
      "Can't reach the Nexus API. Make sure the backend is running.",
    )
  }

  if (!response.ok) throw new Error(await readErrorMessage(response))
  return response.json()
} 


export async function importCustomersCsv(file) {
  const formData = new FormData()
  formData.append('file', file)

  let response
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/customers/upload`, {
      method: 'POST',
      body: formData,
    })
  } catch {
    throw new Error(
      "Can't reach the Nexus API. Make sure the backend is running.",
    )
  }

  if (!response.ok) throw new Error(await readErrorMessage(response))
  return response.json()
} 


export async function listImports(limit = 10) {
  let response
  try {
    response = await fetch(
      `${API_BASE_URL}/api/v1/customers/imports?limit=${limit}`,
    )
  } catch {
    throw new Error(
      "Can't reach the Nexus API. Make sure the backend is running.",
    )
  }

  if (!response.ok) throw new Error(await readErrorMessage(response))
  return response.json()
}



export async function listCustomers({ search, sortBy, sortDir, limit, offset }) {
  const params = new URLSearchParams({
    sort_by: sortBy,
    sort_dir: sortDir,
    limit: String(limit),
    offset: String(offset),
  })
  if (search) params.set('search', search)

  let response
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/customers?${params}`)
  } catch {
    throw new Error(
      "Can't reach the Nexus API. Make sure the backend is running.",
    )
  }

  if (!response.ok) throw new Error(await readErrorMessage(response))
  return response.json()
}