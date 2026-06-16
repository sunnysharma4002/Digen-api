# Digen Image API

A Flask-based API for generating AI images using the Digen.ai platform. Supports multiple models, synchronous and asynchronous generation, and includes a beautiful web interface with real-time loading animations.

## ✨ Features

- 🎨 **Multiple AI Models** – Flux, Flux 2, GPT Image, Sora Image, SeaDream 5, and more
- ⚡ **Sync & Async Modes** – Choose between waiting for results or polling later
- 🌐 **Beautiful Web UI** – Modern interface with ChatGPT-style generation animation
- 🔄 **Real-time Loading Animation** – Bouncing dots, shimmer bar, and rotating status messages
- 📦 **Simple REST API** – Easy to integrate into any application

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone <repo-url>
cd digen-image-api
pip install -r requirements.txt
```

### 2. Configure

Edit `config.py` to set your Digen API token:

```python
DIGEN_TOKEN = "your_api_token_here"
BASE_URL = "https://api.digen.ai"
```

Or set environment variables:

```bash
export DIGEN_TOKEN="your_api_token_here"
export BASE_URL="https://api.digen.ai"
```

### 3. Run

```bash
python api/index.py
```

Or with Flask directly:

```bash
cd api
flask run --port=5001
```

### 4. Open

Visit **http://localhost:5001** to use the web interface.

## 📡 API Endpoints

### `GET /api/generate` or `GET /generate`

Generate an image.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | string | (required) | Text description of the image |
| `model` | string | `flux` | Model to use (see list below) |
| `mode` | string | `sync` | `sync` (wait for result) or `async` (return job ID) |
| `token` | string | (optional) | Override API token |

**Sync response (success):**
```json
{
  "success": true,
  "image_url": "https://..."
}
```

**Async response:**
```json
{
  "success": true,
  "job_id": "...",
  "session_id": "...",
  "status": "processing"
}
```

### `GET /api/status` or `GET /status`

Check the status of an async job.

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | string | Job ID from async response |
| `session_id` | string | Session ID from async response |
| `token` | string | (optional) Override API token |

**Response (processing):**
```json
{ "status": "processing" }
```

**Response (completed):**
```json
{
  "status": "completed",
  "image_url": "https://..."
}
```

## 🧪 Available Models

| Model ID | Description |
|----------|-------------|
| `flux` | Flux (free tier, batch_size=4) |
| `flux2` | Flux 2 |
| `flux2-klein` | Flux 2 Klein |
| `flux-schnell` | Flux Schnell |
| `zimage` | ZImage |
| `sora-image` | Sora Image |
| `gpt-image` | GPT Image 1.5 |
| `gpt-image2` | GPT Image 2 |
| `seedream5` | SeaDream 5 |
| `image-motion` | Image Motion (free) |
| `nano-banana` | Nano Banana |
| `nano-banana2` | Nano Banana 2 |
| `nano-banana2-r` | Nano Banana 2 R |

## 🖼️ Web Interface

The web interface (`index.html`) features:

- **ChatGPT-style loading animation** – bouncing dots with a shimmer progress bar
- **Rotating status messages** – keeps users engaged while waiting
- **Smooth transitions** – fade-in for generated images
- **Dark, modern design** – glassmorphism UI with gradient accents
- **Responsive layout** – works on desktop and mobile

### Loading Animation Preview

The loading state includes:
- Three bouncing dots (like ChatGPT's "thinking" animation)
- A shimmering progress bar
- Rotating status messages that change every 3 seconds
- Messages like "Warming up the neural network...", "Painting pixels with AI magic...", etc.

## 📁 Project Structure

```
├── api/
│   ├── __init__.py
│   └── index.py          # Flask application
├── config.py              # API token & base URL
├── digen_image_api.py     # Core image generation logic
├── index.html             # Web interface
├── test.html              # Simple test page
├── requirements.txt       # Python dependencies
├── vercel.json            # Vercel deployment config
└── README.md
```

## ☁️ Deployment

### Vercel

The project includes a `vercel.json` for serverless deployment on Vercel. Set environment variables in the Vercel dashboard:

- `DIGEN_TOKEN` – Your Digen API token
- `BASE_URL` – Base URL (default: `https://api.digen.ai`)

## 📄 License

MIT
