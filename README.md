# Voice AI Agents with OpenAI & Telnyx

A real-time voice AI assistant system that integrates OpenAI's Realtime API with Telnyx's telephony services to create intelligent voice agents capable of natural conversations over phone calls.

## 🎯 Features

- **Real-time Voice Conversations**: Seamless voice interactions using OpenAI's Realtime API
- **Phone Integration**: Handle inbound/outbound calls through Telnyx telephony services
- **Bidirectional Audio Streaming**: Real-time audio processing with PCMU codec support
- **Configurable AI Personality**: Customizable agent voice, instructions, and greeting messages
- **WebSocket Architecture**: Efficient real-time communication between Telnyx and OpenAI
- **Production Ready**: Built with FastAPI, comprehensive error handling, and logging

## 🏗️ Architecture

The system consists of three main components:

1. **FastAPI Server** - Handles webhooks and WebSocket connections
2. **Telnyx Integration** - Manages phone calls and media streaming
3. **OpenAI Realtime API** - Provides AI-powered voice responses

```
Phone Call → Telnyx → WebSocket → FastAPI → OpenAI Realtime API
                                     ↓
                                 Voice Response
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Telnyx account with API access
- OpenAI account with API access
- Public domain/ngrok for webhook endpoints

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/voice-ai-agents-openai-telnyx.git
   cd voice-ai-agents-openai-telnyx
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration**
   
   Create a `.env` file in the project root:
   ```env
   # Required Configuration
   TELNYX_API_KEY=your_telnyx_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here
   DOMAIN=your-domain.com  # or ngrok URL like abc123.ngrok.io
   
   # Optional Voice & AI Configuration
   AGENT_VOICE=marin  # Options: alloy, echo, fable, onyx, nova, shimmer, marin
   AGENT_INSTRUCTIONS=You are a helpful voice assistant. Greet warmly, then help succinctly. Keep responses concise but informative. Be friendly and professional.
   AGENT_GREETING=Hi! Thanks for calling. How can I help you today?
   ```

4. **Run the application**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

## ⚙️ Telnyx Setup

### 1. Create a Call Control Application

1. Log in to your [Telnyx Portal](https://portal.telnyx.com/)
2. Navigate to **Voice > Call Control**
3. Click **Create New Application**
4. Configure the application:
   - **Application Name**: `Voice AI Agent`
   - **Webhook URL**: `https://your-domain.com/webhook`
   - **HTTP Request Method**: `POST`
   - **Failover URL**: (optional) `https://your-backup-domain.com/webhook`
   - **Connection Type**: `Call Control`

### 2. Purchase and Configure a Phone Number

1. Go to **Numbers > Phone Numbers**
2. Click **Buy Numbers** and select a number
3. Assign the number to your Call Control application:
   - Select your purchased number
   - Click **Settings**
   - Under **Voice Settings**, select your Call Control application
   - Save the configuration

### 3. Configure Webhooks

Ensure your webhook endpoint (`https://your-domain.com/webhook`) is:
- Publicly accessible
- Returns HTTP 200 responses
- Can handle POST requests with JSON payloads

## 🔧 Configuration Options

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELNYX_API_KEY` | ✅ | - | Your Telnyx API key |
| `OPENAI_API_KEY` | ✅ | - | Your OpenAI API key |
| `DOMAIN` | ✅ | - | Your public domain for webhooks |
| `AGENT_VOICE` | ❌ | `marin` | OpenAI voice model |
| `AGENT_INSTRUCTIONS` | ❌ | Default helpful assistant | AI behavior instructions |
| `AGENT_GREETING` | ❌ | Default greeting | Initial message to callers |

### Voice Options

Available OpenAI voice models:
- `alloy` - Balanced, neutral voice
- `echo` - Clear, articulate voice  
- `fable` - Warm, engaging voice
- `onyx` - Deep, authoritative voice
- `nova` - Bright, energetic voice
- `shimmer` - Soft, gentle voice
- `marin` - Conversational, friendly voice

## 📡 API Endpoints

### Health Check
```
GET /health
```
Returns system status and current time.

### Telnyx Webhook
```
POST /webhook
```
Handles Telnyx call events (call.initiated, call.hangup, etc.)

### Media WebSocket
```
WS /telnyx_media
```
Manages real-time audio streaming between Telnyx and OpenAI.

## 🧪 Testing

### Local Development with ngrok

1. **Install ngrok** (if not already installed)
   ```bash
   npm install -g ngrok
   # or
   brew install ngrok
   ```

2. **Start your application**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

3. **Expose with ngrok**
   ```bash
   ngrok http 8000
   ```

4. **Update your .env file**
   ```env
   DOMAIN=your-ngrok-url.ngrok.io
   ```

5. **Update Telnyx webhook URL** to `https://your-ngrok-url.ngrok.io/webhook`

### Test Call Flow

1. Call your Telnyx phone number
2. The system should automatically answer
3. You'll hear the configured greeting
4. Start speaking - the AI will respond in real-time
5. Check logs for detailed event tracking

## 📁 Project Structure

```
voice-ai-agents-openai-telnyx/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application and WebSocket handlers
│   └── utils/
│       ├── __init__.py
│       └── telnyx_http.py   # Telnyx API communication utilities
├── requirements.txt         # Python dependencies
├── .env                    # Environment configuration (not tracked)
├── .gitignore             # Git ignore patterns
└── README.md              # This file
```

## 🔍 Troubleshooting

### Common Issues

**1. Webhook not receiving events**
- Verify your domain is publicly accessible
- Check Telnyx application webhook URL configuration
- Ensure endpoint returns HTTP 200

**2. Audio quality issues**
- Verify PCMU codec configuration
- Check network connectivity and latency
- Monitor WebSocket connection stability

**3. OpenAI connection errors**
- Validate API key permissions
- Check rate limits and quotas
- Monitor WebSocket connection logs

### Debug Mode

Enable detailed logging by setting log level to DEBUG:
```python
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Resources

- [Telnyx Call Control API Documentation](https://developers.telnyx.com/docs/api/v2/call-control)
- [OpenAI Realtime API Documentation](https://platform.openai.com/docs/guides/realtime)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## 📞 Support

For support and questions:
- Create an issue in this repository
- Check the [Telnyx Community](https://developers.telnyx.com/community)
- Review [OpenAI API Documentation](https://platform.openai.com/docs)

---

**Tags**: `voice-ai`, `openai`, `telnyx`, `telephony`, `real-time`, `websocket`, `fastapi`, `python`, `ai-assistant`, `speech-to-text`, `text-to-speech`
