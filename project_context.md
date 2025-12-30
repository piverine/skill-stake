# Skill-Stake Project Context

This document provides a comprehensive overview of the Skill-Stake project, including its purpose, architecture, features, and workflows. It is intended to give Large Language Models (LLMs) full context on the codebase.

## 1. Project Overview

**Skill-Stake** is a "Learn-to-Earn" (or rather, "Stake-to-Learn") platform that combats procrastination by combining AI-powered learning verification with blockchain-based financial incentives.

**Core Concept**: Users upload study materials (PDFs), stake cryptocurrency (ETH) to pledge their commitment to learn, and must pass an AI-generated quiz to retrieve their stake. Failure resulted in slashed stakes.

## 2. Technical Architecture

The project follows a modern microservices architecture:

### Frontend
*   **Framework**: Next.js 14 (App Router)
*   **Language**: TypeScript
*   **Styling**: Tailwind CSS
*   **Key Directories**:
    *   `src/app`: Contains routes for `dashboard`, `quiz`, `upload`, `sign-in`, `sign-up`.
    *   `src/components`: UI components.
    *   `src/lib`: Utility functions and API clients.

### Backend
*   **Framework**: FastAPI
*   **Language**: Python 3.11+
*   **Database**: PostgreSQL (managed by NeonDB)
*   **ORM**: SQLAlchemy with Pydantic for schemas.
*   **AI Integration**: Google Gemini 1.5 Flash (via `google-generativeai` SDK).
*   **Key Directories**:
    *   `app/api`: REST API endpoints (`auth`, `pdf_upload`, `quiz`).
    *   `app/models`: SQLAlchemy database models (`User`, `Stake`, `Quiz`, `PDFUpload`).
    *   `app/schemas`: Pydantic data schemas.

### Blockchain
*   **Network**: Ethereum (Sepolia Testnet)
*   **Development Framework**: Hardhat
*   **Smart Contracts**: Solidity contracts handling staking, locking, and refund/slashing logic.
*   **Interaction**: Frontend triggers transactions; Backend may listen to events or verify status.

## 3. Data Models

### User
*   Stores profile info linked to Clerk authentication ID.
*   Tracks reputation or history.

### PDFUpload
*   Stores metadata of uploaded files (S3/local path).
*   Status: `uploaded`, `processing`, `processed`, `failed`.
*   Content hash for integrity.

### Quiz
*   Generated from parsed PDF content using Gemini.
*   Contains questions, options, correct answers.
*   Status: `generated`, `completed`.
*   Score tracking.

### Stake
*   Links a User, a Quiz/PDF, and a Blockchain Transaction Hash.
*   Status: `locked`, `refunded`, `slashed`.
*   Amount: Staked ETH value.

## 4. User Workflow

1.  **Onboarding**: User sign-up/login via Clerk.
2.  **Upload**: User uploads a PDF document (e.g., lecture notes, technical paper).
3.  **Analysis**: Backend processes PDF, uses Gemini to extract key concepts and generate a quiz schema (hidden from user initially).
4.  **Staking**:
    *   User is presented with a "Stake" requirement.
    *   User initiates a transaction via MetaMask to lock e.g., 0.01 ETH in the smart contract.
    *   Transaction hash is verified by backend.
5.  **Learning & Testing**:
    *   User studies the material.
    *   User takes the AI-generated quiz.
6.  **Resolution**:
    *   **Pass**: Backend verifies score > threshold. Smart contract allows withdrawal/refund of stake.
    *   **Fail**: Stake remains locked or is burned/sent to a treasury (depending on contract logic).

## 5. Key Features & specifics

*   **Anti-Cheat**: Quiz questions are generated dynamically from the specific content of the uploaded document, making generic answers less effective.
*   **Financial Accountability**: leveraging loss aversion to motivate study.
*   **Scalable AI**: Uses Gemini Flash for fast, low-latency text processing and question generation.

## 6. Development Status & Setup

*   **Dockerized**: `docker-compose.yml` orchestrates frontend, backend, and database services.
*   **Migrations**: `alembic` handles database schema changes.
*   **Environment**: Requires `.env` with keys for Clerk, Gemini, Database, and Ethereum RPC.

## 7. Future Roadmap (Implied)
*   Integration with more granular verified credentials.
*   Multi-chain support.
*   Social features (leaderboards, group staking).
