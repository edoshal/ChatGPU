#!/usr/bin/env python3
"""
Test script for Facebook MMS-TTS-VIE integration
"""
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_mms_tts():
    """Test the MMS-TTS-VIE service"""
    try:
        from services import mms_tts
        
        print("🔍 Testing Facebook MMS-TTS-VIE integration...")
        
        # Test availability
        is_available = mms_tts.is_mms_tts_available()
        print(f"✅ MMS-TTS-VIE available: {is_available}")
        
        if not is_available:
            print("❌ MMS-TTS-VIE not available. Please install required dependencies:")
            print("   pip install transformers torch torchaudio librosa numpy scipy")
            return False
        
        # Test model info
        model_info = mms_tts.mms_tts_service.get_model_info()
        print(f"📋 Model info: {model_info}")
        
        # Test text-to-speech
        test_text = "Xin chào! Đây là bài test cho Facebook MMS-TTS-VIE."
        print(f"🎤 Testing TTS with text: '{test_text}'")
        
        audio_url = mms_tts.generate_audio_mms(test_text)
        
        if audio_url:
            print("✅ TTS generation successful!")
            print(f"📊 Audio URL length: {len(audio_url)} characters")
            print(f"🎵 Audio format: {audio_url[:50]}...")
        else:
            print("❌ TTS generation failed!")
            return False
        
        print("\n🎉 All tests passed! MMS-TTS-VIE integration is working correctly.")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please install required dependencies:")
        print("   pip install transformers torch torchaudio librosa numpy scipy")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_mms_tts()
    sys.exit(0 if success else 1) 