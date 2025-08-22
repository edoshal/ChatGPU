# ChromaDB Setup Guide

## Overview
ChromaDB is used for intelligent chat history management and context retrieval. It provides semantic search capabilities to find relevant previous conversations when generating AI responses.

## Prerequisites

### SQLite Version Requirement
ChromaDB requires SQLite version 3.35.0 or higher. Your current system has SQLite 3.31.1.

**Check your SQLite version:**
```bash
python3 -c "import sqlite3; print('SQLite version:', sqlite3.sqlite_version)"
```

## Installation Options

### Option 1: Upgrade SQLite (Recommended for Production)

#### Ubuntu/Debian:
```bash
# Add the deadsnakes PPA for newer Python versions
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update

# Install Python 3.11+ which includes newer SQLite
sudo apt install python3.11 python3.11-venv python3.11-dev

# Create new virtual environment with Python 3.11
python3.11 -m venv .venv_new
source .venv_new/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### CentOS/RHEL:
```bash
# Install newer SQLite
sudo yum install sqlite-devel

# Or use EPEL for newer versions
sudo yum install epel-release
sudo yum install sqlite-devel
```

### Option 2: Use Docker (Alternative)
```bash
# Run the application in Docker with newer SQLite
docker run -it --rm -v $(pwd):/app -p 8000:8000 python:3.11-slim bash
cd /app
pip install -r requirements.txt
uvicorn app.api:app --host 0.0.0.0 --port 8000
```

### Option 3: Fallback Mode (Current Implementation)
The application is designed to work without ChromaDB. When ChromaDB is not available, it falls back to the traditional database-based chat history.

## Installation

### 1. Install Dependencies
```bash
# Install ChromaDB
pip install chromadb

# For GPU support (optional)
pip install chromadb[all]
```

### 2. Verify Installation
```bash
# Run the test script
python3 test_chroma_db.py
```

### 3. First Run
On the first run, ChromaDB will create a local database in the `chroma_db` directory.

## Features

### Advantages of ChromaDB
- ✅ **Semantic Search**: Find relevant context based on meaning, not just keywords
- ✅ **Intelligent Context**: AI responses are more contextual and relevant
- ✅ **Efficient Storage**: Optimized for chat history and retrieval
- ✅ **Privacy**: All data stored locally
- ✅ **Scalable**: Handles large amounts of chat history efficiently

### Current Fallback Features
- ✅ **Database Storage**: Chat messages stored in SQLite database
- ✅ **Recent History**: Last 10 messages used for context
- ✅ **Basic Search**: Keyword-based message retrieval
- ✅ **User Isolation**: Each user's data is properly isolated

## Usage

### Automatic Integration
ChromaDB is automatically integrated into the chat system:

1. **Message Storage**: All chat messages are stored in both database and ChromaDB
2. **Context Retrieval**: When generating AI responses, relevant context is retrieved
3. **Fallback**: If ChromaDB is unavailable, the system uses database storage

### API Endpoints
- `GET /api/chroma/status` - Check ChromaDB status
- `GET /api/chroma/chat-summary/{profile_id}` - Get chat summary
- `DELETE /api/chroma/chat-history/{profile_id}` - Delete chat history

## Troubleshooting

### Common Issues

#### 1. SQLite Version Error
```
RuntimeError: Your system has an unsupported version of sqlite3. Chroma requires sqlite3 >= 3.35.0.
```

**Solutions:**
- Upgrade SQLite (see Installation Options above)
- Use Docker with newer Python/SQLite
- Use fallback mode (automatic)

#### 2. Import Error
```
ModuleNotFoundError: No module named 'chromadb'
```

**Solution**: Install ChromaDB:
```bash
pip install chromadb
```

#### 3. Permission Errors
```
PermissionError: [Errno 13] Permission denied
```

**Solution**: Check directory permissions:
```bash
chmod 755 chroma_db/
```

#### 4. Memory Issues
**Solution**: 
- Ensure sufficient RAM (2GB+ recommended)
- Monitor disk space for ChromaDB storage
- Consider limiting context retrieval size

## Performance Tips

1. **First Run**: ChromaDB initialization may take a few seconds
2. **Storage**: ChromaDB data is stored in `chroma_db/` directory
3. **Context Size**: Default context retrieval is limited to 8-10 messages
4. **Cleanup**: Use API endpoints to clean up old chat history

## Comparison: ChromaDB vs Database Only

| Feature | ChromaDB Enabled | Database Only |
|---------|------------------|---------------|
| Context Relevance | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Response Quality | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Storage Efficiency | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Setup Complexity | Medium | Easy |
| Resource Usage | Higher | Lower |
| Semantic Search | ✅ | ❌ |

## Migration

### From Database to ChromaDB
1. Install ChromaDB following the setup guide
2. The system will automatically start using ChromaDB
3. Existing chat history will be gradually indexed
4. No data migration required

### From ChromaDB to Database Only
1. ChromaDB can be disabled by not installing it
2. System automatically falls back to database storage
3. No data loss - all messages remain in database

## Support

If you encounter issues:
1. Check the console logs for error messages
2. Run `python3 test_chroma_db.py` to verify installation
3. Ensure SQLite version is 3.35.0+
4. Check available system resources (RAM, disk space)
5. Use fallback mode if ChromaDB setup is problematic

## Current Status

**Fallback Mode Active**: The application is currently running in fallback mode due to SQLite version incompatibility. All chat functionality works normally using the traditional database storage.

To enable ChromaDB features, please upgrade SQLite to version 3.35.0 or higher. 