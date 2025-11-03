# SQL RAG Application 🐕

A modern RAG (Retrieval-Augmented Generation) application for natural language SQL querying, built with FastAPI + React. Migrated from Streamlit for better scalability and user experience.

## 🚀 Features

- **🤖 AI-Powered SQL Generation**: Translate natural language to optimized SQL queries
- **💬 Real-time Chat**: WebSocket-powered streaming responses
- **📊 SQL Execution**: Safe query execution with cost controls
- **🗂️ Schema Explorer**: Interactive database schema browsing
- **🔍 Query Catalog**: Searchable collection of pre-built queries
- **📈 Analytics**: Query statistics and usage insights
- **🎯 Specialized Agents**: @create, @explain, @schema, @longanswer modes
- **💾 Conversation Persistence**: Save and resume conversations
- **📱 Responsive Design**: Mobile and tablet friendly

## 📁 Project Structure

```
sql-rag-app/
├── backend/                    # FastAPI backend
│   ├── app.py                 # Main FastAPI application
│   ├── api/                   # API route handlers
│   │   ├── chat.py           # Chat endpoints
│   │   ├── data.py           # Data endpoints
│   │   └── sql.py            # SQL execution endpoints
│   ├── models/               # Pydantic models/schemas
│   └── services/             # Business logic services
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/           # Page components
│   │   ├── hooks/           # Custom React hooks
│   │   ├── services/        # API services
│   │   ├── store/           # Redux state management
│   │   └── types/           # TypeScript type definitions
│   └── package.json
├── rag_app/                   # Original Streamlit app (reference)
├── docker-compose.yml         # Development environment
└── README.md
```

## 🛠️ Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **Pydantic**: Data validation and serialization
- **WebSockets**: Real-time communication
- **BigQuery**: Database backend
- **Gemini AI**: Language model for RAG

### Frontend
- **React 18**: Modern UI framework
- **TypeScript**: Type-safe development
- **Redux Toolkit**: State management
- **React Router**: Client-side routing
- **Modern CSS**: Responsive design

### Infrastructure
- **Docker**: Containerization
- **Nginx**: Reverse proxy
- **Docker Compose**: Development orchestration

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ and npm
- Python 3.10+
- Docker and Docker Compose
- Google Cloud credentials for BigQuery and Vertex AI (service account or ADC)
- Optional: Gemini API key (only if you choose public API mode)

### Environment Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd SQL_RAG/rag_app
   ```

2. **Set up environment variables**:
   ```bash
   # Create .env file
   cp .env.example .env
   
   # Edit .env with your credentials
   nano .env
   ```

   Required environment variables for Vertex AI SDK mode:
   ```env
   GENAI_CLIENT_MODE=sdk
   GOOGLE_CLOUD_PROJECT=your_project_id
   GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json
   BIGQUERY_PROJECT_ID=your_project_id
   BIGQUERY_DATASET=your_default_dataset
   VECTOR_STORE_NAME=index_sample_queries_with_metadata_recovered
   ```

   For local development you can run `gcloud auth application-default login` instead of
   providing a service-account JSON key. If you need to fall back to the public Gemini API,
   set `GENAI_CLIENT_MODE=api` and supply `GEMINI_API_KEY` (or `GOOGLE_API_KEY`).
   Update `GOOGLE_GENAI_USE_VERTEXAI` if you need to force embeddings through a specific path.

### Development Mode

1. **Using Docker Compose (Recommended)**:
   ```bash
   docker-compose up --build
   ```
   The application will be available at:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

2. **Manual Development Setup**:
   
   **Backend**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -e .
   uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload
   ```
   
   **Frontend**:
   ```bash
   cd frontend
   npm install
   echo "VITE_API_BASE_URL=http://localhost:8080" > .env.local
   npm run dev -- --host 127.0.0.1 --port 5173
   ```

### Generate Gemini Embeddings

With `GENAI_CLIENT_MODE=sdk` configured, use the helper script to build the FAISS vector store:

```bash
python standalone_embedding_generator.py --csv sample_queries_with_metadata.csv
```

Pass your own CSV of queries or descriptions if you are onboarding work data. The script
stores the resulting index under `faiss_indices/` with the name from `VECTOR_STORE_NAME`.
You can rerun it any time you need to regenerate embeddings for new datasets.

For a detailed walkthrough of the full workstation setup (including vector store generation),
see `docs/WORKSTATION_SETUP.md`.

## 📖 Usage

### Chat Interface
1. Navigate to http://localhost:3000/chat
2. Start asking questions in plain English:
   - "Show me top 10 customers by order total"
   - "What are the most popular products?"
3. Use specialized agents:
   - `@create`: Generate SQL queries
   - `@explain`: Explain query logic
   - `@schema`: Explore database structure
   - `@longanswer`: Get detailed explanations

### Query Search
1. Go to http://localhost:3000/search
2. Browse the catalog of pre-built SQL queries
3. Use filters to find queries by tables, complexity, etc.
4. Copy queries directly to clipboard

### Data Schema
1. Visit http://localhost:3000/data
2. Explore database tables and relationships
3. Understand column types and constraints
4. Visualize table joins

### Analytics
1. Check http://localhost:3000/analytics
2. View query execution statistics
3. Monitor token usage and costs
4. Analyze query patterns

## 🔧 Configuration

### Backend Configuration

Update `backend/app.py` settings:
- CORS origins
- WebSocket connection limits
- Rate limiting
- Logging levels

### Frontend Configuration

Update `frontend/src/utils/constants.ts`:
- API endpoints
- WebSocket URLs
- UI preferences
- Feature flags

## 📚 API Documentation

### Main Endpoints

- `POST /api/chat/query` - Send chat query
- `POST /api/chat/execute-sql` - Execute SQL
- `GET /api/data/schema` - Get database schema
- `GET /api/data/analytics` - Get analytics
- `GET /api/data/queries` - Get query catalog
- `WS /ws/chat/{session_id}` - Real-time chat

Interactive documentation available at: http://localhost:8000/docs

## 🚀 Deployment

### Production Docker Deployment

1. **Build and deploy**:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

2. **Configure nginx** for SSL/HTTPS:
   ```bash
   # Edit nginx/nginx.conf
   nano nginx/nginx.conf
   ```

3. **Monitor logs**:
   ```bash
   docker-compose logs -f
   ```

### Cloud Deployment Options

- **Google Cloud Run**: Backend auto-scaling
- **Vercel**: Frontend hosting
- **AWS ECS**: Container orchestration
- **DigitalOcean**: All-in-one platform

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest tests/ -v
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Integration Tests
```bash
# Run full application tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## 📝 Migration from Streamlit

This application was migrated from a Streamlit version. Key improvements:

- ✅ Real-time streaming via WebSockets
- ✅ Better responsive design
- ✅ Mobile-friendly interface
- ✅ Improved state management
- ✅ Production-ready architecture
- ✅ Better performance and scalability

Migration details are documented in [`STREAMLIT_TO_FASTAPI_REACT_MIGRATION_ROADMAP.md`](STREAMLIT_TO_FASTAPI_REACT_MIGRATION_ROADMAP.md)

## 🐛 Troubleshooting

### Common Issues

1. **WebSocket connection failed**:
   - Check backend is running on port 8000
   - Verify CORS settings match frontend URL
   - Check firewall/proxy settings

2. **BigQuery connection errors**:
   - Verify service account credentials
   - Check project ID and permissions
   - Ensure BigQuery API is enabled

3. **Gemini API errors**:
   - Verify API key is valid
   - Check rate limits and quotas
   - Ensure proper request formatting

4. **Frontend build errors**:
   - Clear node_modules and reinstall
   - Check Node.js version compatibility
   - Verify TypeScript configuration

### Debug Mode

Enable debug logging:
```bash
# Backend
DEBUG=1 python backend/app.py

# Frontend
LOG_LEVEL=debug npm start
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Guidelines
- Follow TypeScript and Python best practices
- Write tests for new features
- Update documentation
- Use conventional commit messages
- Ensure all checks pass

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Original Streamlit application architecture
- FastAPI and React communities
- Google Cloud Platform services
- Gemini AI platform
- All contributors and users

## 📞 Support

- 📧 Email: support@example.com
- 💬 Discord: [Community Server]
- 🐛 Issues: [GitHub Issues]
- 📖 Documentation: [Wiki]

---

Made with ❤️ by pikushi 🐕

#codepuppy
