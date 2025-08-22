# Facebook MMS-TTS-VIE Setup Guide

## Overview
Facebook MMS-TTS-VIE is a Vietnamese text-to-speech model that provides an alternative to Azure Speech Service. It runs locally and doesn't require an API key.

## Installation

### 1. Install Dependencies
```bash
# Install required Python packages
pip install transformers torch torchaudio librosa numpy scipy

# For GPU support (optional but recommended)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 2. Verify Installation
```bash
# Run the test script
python test_mms_tts.py
```

### 3. First Run
On the first run, the model will be downloaded automatically from Hugging Face (approximately 1GB). This may take a few minutes depending on your internet connection.

## Usage

### In the Web Interface
1. Start a chat with the AI
2. When you receive a response, you'll see two audio buttons:
   - **Blue sound button with "M" indicator**: Uses MMS-TTS-VIE
   - **Gray sound button**: Uses Azure Speech Service

### API Endpoints
- `POST /api/mms-tts/generate` - Generate audio from text
- `GET /api/mms-tts/status` - Check service status

## Features

### Advantages of MMS-TTS-VIE
- ✅ **No API key required** - runs completely locally
- ✅ **Vietnamese optimized** - specifically trained for Vietnamese
- ✅ **High quality** - neural voice synthesis
- ✅ **Privacy** - no data sent to external services
- ✅ **Offline capable** - works without internet after initial download

### Limitations
- ⚠️ **Large model size** - ~1GB download required
- ⚠️ **Slower first run** - model needs to be loaded into memory
- ⚠️ **CPU intensive** - requires more computational resources
- ⚠️ **No speech-to-text** - only text-to-speech functionality

## Troubleshooting

### Common Issues

#### 1. Import Error
```
ModuleNotFoundError: No module named 'transformers'
```
**Solution**: Install the required packages:
```bash
pip install transformers torch torchaudio librosa numpy scipy
```

#### 2. CUDA Out of Memory
```
RuntimeError: CUDA out of memory
```
**Solution**: The model will automatically fall back to CPU if GPU memory is insufficient.

#### 3. Slow Performance
**Solution**: 
- Ensure you have sufficient RAM (4GB+ recommended)
- Consider using a GPU if available
- The first run is always slower due to model loading

#### 4. Model Download Issues
**Solution**:
- Check your internet connection
- Try running the test script again
- The model will be cached locally after first download

## Configuration

### Environment Variables
No environment variables are required for MMS-TTS-VIE. The service works out of the box once dependencies are installed.

### Model Configuration
The model uses these default settings:
- **Model**: `facebook/mms-tts-vie`
- **Sample Rate**: 24000 Hz
- **Format**: WAV
- **Language**: Vietnamese

## Performance Tips

1. **First Run**: Be patient during the first run as the model loads
2. **Memory**: Ensure you have at least 4GB of available RAM
3. **GPU**: If available, the model will automatically use GPU acceleration
4. **Caching**: The model is cached in memory after first load for faster subsequent runs

## Comparison with Azure Speech Service

| Feature | MMS-TTS-VIE | Azure Speech Service |
|---------|-------------|---------------------|
| API Key Required | ❌ | ✅ |
| Internet Required | ❌ (after download) | ✅ |
| Vietnamese Quality | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Setup Complexity | Medium | Easy |
| Cost | Free | Pay-per-use |
| Speech-to-Text | ❌ | ✅ |
| Multiple Voices | ❌ | ✅ |

## Support

If you encounter issues:
1. Check the console logs for error messages
2. Run `python test_mms_tts.py` to verify installation
3. Ensure all dependencies are properly installed
4. Check available system resources (RAM, disk space) 