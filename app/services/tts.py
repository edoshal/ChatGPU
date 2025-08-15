"""
Text-to-Speech service using Azure Speech Services
"""
import os
import io
import base64
import logging
from typing import Optional

try:
    import azure.cognitiveservices.speech as speechsdk
except ImportError:
    raise RuntimeError("Missing dependency 'azure-cognitiveservices-speech'. Please install with: pip install azure-cognitiveservices-speech")

# Logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("azure_tts")


class AzureSpeechService:
    def __init__(self):
        self.speech_config = None
        self._initialized = False
        
        # Azure Speech Service configuration
        self.speech_key = os.getenv("AZURE_SPEECH_KEY")
        self.speech_region = os.getenv("AZURE_SPEECH_REGION", "southeastasia")
        self.voice_name = "vi-VN-HoaiMyNeural"  # Vietnamese Neural voice
        
    def _initialize_service(self):
        """Khởi tạo Azure Speech Service (lazy loading)"""
        if self._initialized:
            return
            
        if not self.speech_key:
            logger.error("AZURE_SPEECH_KEY not found in environment variables")
            raise ValueError("Azure Speech Key is required. Please set AZURE_SPEECH_KEY environment variable")
            
        try:
            logger.info("Initializing Azure Speech Service...")
            self.speech_config = speechsdk.SpeechConfig(
                subscription=self.speech_key,
                region=self.speech_region
            )
            
            # Cấu hình voice và audio format
            self.speech_config.speech_synthesis_voice_name = self.voice_name
            self.speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
            )
            
            self._initialized = True
            logger.info(f"Azure Speech Service initialized successfully with voice: {self.voice_name}")
            
        except Exception as e:
            logger.error(f"Error initializing Azure Speech Service: {str(e)}")
            raise
    
    def text_to_speech(self, text: str, max_length: int = 1000) -> Optional[str]:
        """
        Chuyển đổi text thành audio sử dụng Azure Speech Service
        
        Args:
            text: Văn bản cần chuyển đổi
            max_length: Độ dài tối đa của text
            
        Returns:
            Base64 encoded audio data URL hoặc None nếu có lỗi
        """
        if not text or not text.strip():
            return None
            
        # Cắt ngắn text nếu quá dài
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        try:
            # Khởi tạo service nếu chưa được tải
            self._initialize_service()
            
            # Tiền xử lý text
            text = self._preprocess_text(text)
            
            # Tạo SSML để có thể điều chỉnh giọng nói
            ssml = self._create_ssml(text)
            
            # Tạo synthesizer
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config,
                audio_config=None  # Sử dụng default để lấy audio data
            )
            
            # Sinh audio
            logger.info(f"Synthesizing text: {text[:50]}...")
            result = synthesizer.speak_ssml_async(ssml).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                # Chuyển đổi audio data thành base64
                audio_data = result.audio_data
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                
                # Trả về data URL cho MP3
                return f"data:audio/mp3;base64,{audio_base64}"
                
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = speechsdk.CancellationDetails(result)
                logger.error(f"Speech synthesis canceled: {cancellation_details.reason}")
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    logger.error(f"Error details: {cancellation_details.error_details}")
                return None
            else:
                logger.error(f"Unexpected result reason: {result.reason}")
                return None
                
        except Exception as e:
            logger.error(f"Azure TTS error: {str(e)}")
            return None
    
    def _create_ssml(self, text: str) -> str:
        """Tạo SSML cho Azure Speech Service"""
        ssml = f"""
        <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="vi-VN">
            <voice name="{self.voice_name}">
                <prosody rate="0.9" pitch="+0%">
                    {text}
                </prosody>
            </voice>
        </speak>
        """
        return ssml.strip()
    
    def _preprocess_text(self, text: str) -> str:
        """Tiền xử lý text cho TTS tiếng Việt"""
        # Loại bỏ các ký tự đặc biệt không cần thiết
        text = text.strip()
        
        # Thay thế một số từ viết tắt phổ biến cho tiếng Việt
        replacements = {
            "kg": "ki-lô-gam",
            "cm": "xen-ti-mét", 
            "mm": "mi-li-mét",
            "km": "ki-lô-mét",
            "°C": "độ C",
            "%": "phần trăm",
            "&": "và",
            "@": "a còng",
            "vs": "so với",
            "AI": "A-I",
            "API": "A-P-I",
            "URL": "U-R-L",
            "=": "bằng",
            "HTTP": "H-T-T-P",
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Loại bỏ markdown formatting
        text = text.replace("**", "").replace("*", "").replace("_", "")
        text = text.replace("```", "").replace("`", "")
        
        # Loại bỏ các ký tự đặc biệt có thể gây lỗi SSML
        text = text.replace("<", "").replace(">", "").replace("&", "và")
        
        # Loại bỏ dấu xuống dòng liên tiếp
        text = " ".join(text.split())
        
        return text
    
    def is_available(self) -> bool:
        """Kiểm tra xem Azure Speech Service có khả dụng không"""
        try:
            import azure.cognitiveservices.speech
            return bool(self.speech_key)
        except ImportError:
            return False
    
    def speech_to_text(self, audio_data: bytes) -> Optional[str]:
        """
        Chuyển đổi audio thành text sử dụng Azure Speech Service
        
        Args:
            audio_data: Raw audio data (WAV format)
            
        Returns:
            Recognized text hoặc None nếu có lỗi
        """
        try:
            # Khởi tạo service nếu chưa được tải
            self._initialize_service()
            
            # Tạo audio input stream từ audio data
            audio_stream = speechsdk.audio.PushAudioInputStream()
            audio_config = speechsdk.audio.AudioConfig(stream=audio_stream)
            
            # Cấu hình recognition
            recognition_config = speechsdk.SpeechConfig(
                subscription=self.speech_key,
                region=self.speech_region
            )
            recognition_config.speech_recognition_language = "vi-VN"
            
            # Tạo recognizer
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=recognition_config,
                audio_config=audio_config
            )
            
            # Push audio data
            audio_stream.write(audio_data)
            audio_stream.close()
            
            # Thực hiện recognition
            logger.info(f"Starting speech recognition... Audio size: {len(audio_data)} bytes")
            
            # Detect audio format for debugging
            audio_format = "unknown"
            if audio_data.startswith(b'RIFF'):
                audio_format = "WAV"
            elif audio_data.startswith(b'OggS'):
                audio_format = "OGG"  
            elif b'webm' in audio_data[:100].lower():
                audio_format = "WebM"
                
            logger.info(f"Detected audio format: {audio_format}")
            
            result = recognizer.recognize_once()
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                logger.info(f"Recognized: {result.text}")
                return result.text
            elif result.reason == speechsdk.ResultReason.NoMatch:
                logger.warning("No speech could be recognized")
                return None
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = speechsdk.CancellationDetails(result)
                logger.error(f"Speech recognition canceled: {cancellation_details.reason}")
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    logger.error(f"Error details: {cancellation_details.error_details}")
                return None
            else:
                logger.error(f"Unexpected recognition result: {result.reason}")
                return None
                
        except Exception as e:
            logger.error(f"Speech recognition error: {str(e)}")
            return None
    
    def get_available_voices(self):
        """Lấy danh sách giọng nói Vietnamese có sẵn"""
        return [
            "vi-VN-HoaiMyNeural",  # Female
            "vi-VN-NamMinhNeural", # Male
        ]


# Singleton instance
azure_speech_service = AzureSpeechService()


def generate_audio(text: str) -> Optional[str]:
    """
    Helper function để sinh audio từ text sử dụng Azure Speech
    
    Args:
        text: Văn bản cần chuyển đổi
        
    Returns:
        Base64 encoded audio data URL hoặc None
    """
    return azure_speech_service.text_to_speech(text)


def recognize_speech(audio_data: bytes) -> Optional[str]:
    """
    Helper function để nhận diện giọng nói thành text
    
    Args:
        audio_data: Raw audio data (WAV format)
        
    Returns:
        Recognized text hoặc None
    """
    return azure_speech_service.speech_to_text(audio_data)


def is_speech_available() -> bool:
    """Kiểm tra xem Azure Speech Service có khả dụng không"""
    return azure_speech_service.is_available()


# Backward compatibility
def is_tts_available() -> bool:
    """Kiểm tra xem Azure TTS có khả dụng không"""
    return azure_speech_service.is_available()
