# Skill-Stake Learning Platform

A blockchain-incentivized learning verification platform that combines AI-powered quiz generation with cryptocurrency staking to create accountability in learning.
## 🌐 Links:
[![Youtube](https://img.shields.io/badge/Youtube-%23E4405F.svg?logo=Youtube&logoColor=white)](https://youtu.be/GLLPoS7QFms) [![LinkedIn](https://img.shields.io/badge/LinkedIn-%230077B5.svg?logo=linkedin&logoColor=white)](https://www.linkedin.com/posts/rohan-kumar-3288671a7_hackxios2k25-kiroide-aws-activity-7411821294603739136-fcLr?utm_source=share&utm_medium=member_desktop&rcm=ACoAAEaO-fwB_zRQlgznfXDeL5BeWi6WGC2dBx0) [![Blog](https://img.shields.io/badge/Blog-black.svg?logo=Blog&logoColor=white)](https://medium.com/@darkgods173/web3-meets-edtech-how-i-used-kiro-gemini-to-gamify-learning-334ca19be1c3)
[![Documentation](https://img.shields.io/badge/Documentation-Blue.svg?logo=Blog&logoColor=white)](https://docs.google.com/document/d/10a6mlKO0SUI7eGGiPCVZeZNBIUHGb_7zWNmUCniNju4/edit?usp=sharing)

## Architecture

- **Frontend**: Next.js 14 with TypeScript and Tailwind CSS
- **Backend**: FastAPI with Python
- **Database**: PostgreSQL (NeonDB in production)
- **Authentication**: Clerk
- **AI**: Gemini 3 Flash API
- **Blockchain**: Ethereum (Sepolia testnet)
- **Development**: Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Environment Setup

1. Copy environment files:
```bash
cp .env.example .env
cp frontend/.env.local.example frontend/.env.local
```

2. Fill in your API keys and configuration in both `.env` files:
   - Clerk authentication keys
   - Gemini API key
   - Ethereum RPC URL (Infura/Alchemy)

### Development with Docker

1. Start all services:
```bash
docker-compose up -d
```

2. Run database migrations:
```bash
docker-compose exec backend alembic upgrade head
```

3. Access the applications:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Local Development

#### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up database
alembic upgrade head

# Run development server
uvicorn app.main:app --reload
```

#### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
skill-stake/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── core/           # Core configuration
│   │   ├── models/         # Database models
│   │   └── main.py         # FastAPI app
│   ├── alembic/            # Database migrations
│   └── requirements.txt
├── frontend/               # Next.js frontend
│   ├── src/
│   │   ├── app/           # App router pages
│   │   └── lib/           # Utilities
│   └── package.json
├── docker-compose.yml      # Development environment
└── .env.example           # Environment variables template
```

## Database Schema

The platform uses PostgreSQL with the following main tables:

- **users**: User profiles linked to Clerk authentication
- **stakes**: ETH stakes with transaction tracking
- **quizzes**: AI-generated quizzes and user responses
- **pdf_uploads**: Uploaded study materials and processing status

## API Endpoints

- `GET /` - Health check
- `GET /api/v1/status` - API status
- More endpoints will be added in subsequent tasks

## Development Workflow

1. **Task 1**: ✅ Project structure and infrastructure setup
2. **Task 2**: Authentication and security layer
3. **Task 3**: Database models and data layer
4. **Task 4**: PDF processing and AI integration
5. **Task 5**: Smart contract and blockchain integration
6. **Task 6**: Quiz taking and scoring system
7. **Task 7**: Settlement and payout system
8. **Task 8**: Error handling and validation
9. **Task 9**: Integration and testing



## Contributing


This project follows the spec-driven development methodology. See `.kiro/specs/skill-stake-learning/` for detailed requirements, design, and implementation tasks.
