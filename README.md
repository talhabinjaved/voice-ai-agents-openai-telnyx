# Voice AI Agents with OpenAI Realtime API & Telnyx

A sophisticated real-time voice AI assistant system that integrates OpenAI's Realtime API with Telnyx's telephony services to create intelligent voice agents capable of natural conversations, call transfers, and call management over phone calls.

## 🎯 Features

- **Real-time Voice Conversations**: Seamless voice interactions using OpenAI's Realtime API
- **Phone Integration**: Handle inbound/outbound calls through Telnyx telephony services
- **Function Tools**: Smart call management with transfer and end call capabilities
- **Dynamic Department Configuration**: Configurable call routing to different departments
- **Bidirectional Audio Streaming**: Real-time audio processing with PCMU codec support
- **Configurable AI Personality**: Customizable agent voice, instructions, and greeting messages
- **WebSocket Architecture**: Efficient real-time communication between Telnyx and OpenAI
- **Production Ready**: Built with FastAPI, comprehensive error handling, and logging

## 🏗️ Architecture

The system consists of three main components working together with function tools:

1. **FastAPI Server** - Handles webhooks, WebSocket connections, and function execution
2. **Telnyx Integration** - Manages phone calls, media streaming, and call transfers
3. **OpenAI Realtime API** - Provides AI-powered voice responses with function calling

```text
Phone Call → Telnyx → WebSocket → FastAPI → OpenAI Realtime API
                                     ↓            ↓
                              Function Tools  Voice Response
                              (Transfer/End)      ↓
                                     ↓        Audio Stream
                                Call Actions ← WebSocket
```

## 🚀 Quick Start

### Prerequisites

- Python 3.12
- Telnyx account with API access
- OpenAI account with Realtime API access
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
   AGENT_INSTRUCTIONS=You are a helpful voice assistant for our company. Be friendly and professional.
   AGENT_GREETING=Hello! Thank you for calling. I'm your AI assistant and I'm here to help you today. How can I assist you?

   # Department Transfer Configuration (Optional)
   SALES_SIP_URI=sip:sales@your-domain.com
   SALES_P_Called_Party_ID_HEADER=sip:sales@your-domain.com

   SUPPORT_SIP_URI=sip:support@your-domain.com
   SUPPORT_P_Called_Party_ID_HEADER=sip:support@your-domain.com

   BILLING_SIP_URI=sip:billing@your-domain.com
   BILLING_P_Called_Party_ID_HEADER=sip:billing@your-domain.com

   TECHNICAL_SIP_URI=sip:tech@your-domain.com
   TECHNICAL_P_Called_Party_ID_HEADER=sip:tech@your-domain.com

   MANAGEMENT_SIP_URI=sip:manager@your-domain.com
   MANAGEMENT_P_Called_Party_ID_HEADER=sip:manager@your-domain.com
   ```

4. **Run the application**

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

## 🛠️ Function Tools

The system includes intelligent function tools that enable the AI to manage calls effectively:

### 1. End Call (`end_call`)

- **Purpose**: Terminates the current phone call gracefully
- **Triggers**: When caller says goodbye, conversation is complete, or escalation needed
- **Parameters**:
  - `reason`: Why the call is ending (`conversation_complete`, `caller_request`, `escalation_needed`)
- **Example**: "Thank you for calling! Have a wonderful day!" → _Call ends_

### 2. Transfer Call (`transfer_call`)

- **Purpose**: Routes calls to appropriate departments
- **Triggers**: When caller needs specialized assistance
- **Parameters**:
  - `department`: Target department (dynamically configured)
  - `reason`: Explanation for the transfer
- **Example**: "I'll transfer you to our billing department now" → _Call transfers_

### Conditional Function Loading

- **No Departments Configured**: Only `end_call` function available
- **Departments Configured**: Both `end_call` and `transfer_call` functions available
- **Dynamic Instructions**: AI instructions automatically adjust based on available functions

## ⚙️ Department Configuration

### Department Environment Variables

Configure each department with SIP URI and custom headers:

```env
# Department Format: {DEPARTMENT}_SIP_URI and {DEPARTMENT}_P_Called_Party_ID_HEADER
SALES_SIP_URI=sip:sales@your-pbx.com
SALES_P_Called_Party_ID_HEADER=sip:400@your-pbx.com

SUPPORT_SIP_URI=sip:support@your-pbx.com
SUPPORT_P_Called_Party_ID_HEADER=sip:401@your-pbx.com
```

### Adding Custom Departments

1. **Add Environment Variables**:

   ```env
   LEGAL_SIP_URI=sip:legal@your-domain.com
   LEGAL_P_Called_Party_ID_HEADER=sip:legal@your-domain.com
   ```

2. **Update Configuration**:
   Edit `app/agent_config.py` to include the new department:

   ```python
   DEPARTMENTS = {
       # ... existing departments ...
       "legal": {
           "sip_uri": os.getenv("LEGAL_SIP_URI", "sip:legal@your-domain.com"),
           "headers": [
               {
                   "name": "P_Called_Party_ID",
                   "value": os.getenv("LEGAL_P_Called_Party_ID_HEADER", "sip:legal@your-domain.com")
               }
           ]
       }
   }
   ```

## 🔧 Telnyx Setup

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

## 📋 Configuration Reference

### Environment Variables

| Variable                          | Required | Default           | Description                         |
| --------------------------------- | -------- | ----------------- | ----------------------------------- |
| `TELNYX_API_KEY`                  | ✅       | -                 | Your Telnyx API key                 |
| `OPENAI_API_KEY`                  | ✅       | -                 | Your OpenAI API key                 |
| `DOMAIN`                          | ✅       | -                 | Your public domain for webhooks     |
| `AGENT_VOICE`                     | ❌       | `marin`           | OpenAI voice model                  |
| `AGENT_INSTRUCTIONS`              | ❌       | Default assistant | AI behavior instructions            |
| `AGENT_GREETING`                  | ❌       | Default greeting  | Initial message to callers          |
| `{DEPT}_SIP_URI`                  | ❌       | Default SIP       | Department SIP endpoint             |
| `{DEPT}_P_Called_Party_ID_HEADER` | ❌       | Default header    | Department P_Called_Party_ID header |

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

```http
GET /health
```

Returns system status and current time.

### Telnyx Webhook

```http
POST /webhook
```

Handles Telnyx call events:

- `call.initiated` - Answers calls and starts streaming
- `call.hangup` - Cleans up call resources
- Other call control events

### Media WebSocket

```http
WebSocket /telnyx_media
```

Manages real-time audio streaming:

- Receives audio from Telnyx
- Forwards to OpenAI Realtime API
- Streams AI responses back to caller
- Handles function call execution

## 🎯 Call Flow Examples

### Basic Conversation

```text
👤 Caller: "Hi, how are you?"
🤖 AI: "Hello! I'm doing great, thank you. How can I assist you today?"
👤 Caller: "I need help with my account"
🤖 AI: "I'd be happy to help. Could you tell me more about the issue?"
```

### Call Transfer

```text
👤 Caller: "I need to speak to billing"
🤖 AI: "Of course! I'll transfer you to our billing department now. Please hold on just a moment while I connect you."
🔄 System: Executes transfer_call function
📞 Result: Call routes to billing department
```

### Call End

```text
👤 Caller: "Thank you, goodbye"
🤖 AI: "Thank you so much for calling! Have a wonderful day!"
🔄 System: Executes end_call function
📞 Result: Call terminates gracefully
```

## 🧪 Testing

### Local Development with ngrok

1. **Install ngrok**

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

4. **Update configuration**

   ```env
   DOMAIN=your-ngrok-url.ngrok.io
   ```

5. **Update Telnyx webhook URL** to `https://your-ngrok-url.ngrok.io/webhook`

### Test Scenarios

1. **Basic Call**: Call your number and have a conversation
2. **Transfer Test**: Ask to be transferred to different departments
3. **End Call Test**: Say goodbye and verify call ends properly
4. **Function Logs**: Monitor logs for function call execution

## 📁 Project Structure

```text
voice-ai-agents-openai-telnyx/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app & WebSocket handlers
│   ├── agent_config.py         # AI configuration & departments
│   └── utils/
│       ├── __init__.py
│       ├── telnyx_http.py      # Telnyx API utilities
│       └── function_tools.py   # Function calling logic
├── requirements.txt            # Python dependencies
├── .env                       # Environment configuration
├── .gitignore                # Git ignore patterns
└── README.md                 # This documentation
```

## 🔍 Troubleshooting

### Common Issues

### 1. Function tools not working

- Verify OpenAI API has Realtime access
- Check function tool configuration in logs
- Ensure departments are properly configured

### 2. Transfer failures

- Validate SIP URIs and headers
- Check Telnyx call control permissions
- Verify department configuration

### 3. Audio issues

- Confirm PCMU codec support
- Check WebSocket connection stability
- Monitor network latency

### 4. Webhook problems

- Verify public domain accessibility
- Check Telnyx webhook configuration
- Ensure proper HTTP response codes

### Debug Mode

Enable detailed logging:

```python
logging.basicConfig(level=logging.DEBUG)
```

Monitor function calls:

```bash
# Look for these log patterns
INFO:app.main:Function call request: transfer_call
INFO:app.utils.function_tools:Executing transfer for call
INFO:app.main:Terminal function transfer_call completed
```

## 🚀 Production Deployment

### Recommended Setup

1. **Use a reliable hosting platform** (AWS, GCP, Azure, Railway, Fly.io)
2. **Configure proper SSL/TLS** for webhook security
3. **Set up monitoring and logging** for call analytics
4. **Implement rate limiting** for API protection
5. **Use environment-specific configurations**

### Environment Variables for Production

```env
# Production settings
TELNYX_API_KEY=prod_key_here
OPENAI_API_KEY=prod_key_here
DOMAIN=your-production-domain.com

# Monitoring
LOG_LEVEL=INFO
SENTRY_DSN=your_sentry_dsn  # Optional

# Rate limiting
MAX_CONCURRENT_CALLS=50
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
- [OpenAI Function Calling Guide](https://platform.openai.com/docs/guides/function-calling)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## 📞 Support

For support and questions:

- Create an issue in this repository
- Check the [Telnyx Community](https://developers.telnyx.com/community)
- Review [OpenAI API Documentation](https://platform.openai.com/docs)

---

## Built with ❤️ using OpenAI Realtime API & Telnyx

**Tags**: `voice-ai`, `openai-realtime`, `telnyx`, `telephony`, `function-calling`, `call-transfer`, `websocket`, `fastapi`, `python`, `ai-assistant`, `real-time-audio`
