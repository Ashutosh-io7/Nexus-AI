const API_BASE_URL = 
    import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000' 

export async function getHealth () {
    const response = await fetch(`${API_BASE_URL}/health`) 
    // /health answers with status 503 when the database is down,
    // but the body still tells us what is wrong.
    return response.json()
}