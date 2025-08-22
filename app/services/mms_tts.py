"""
Text-to-Speech service using Facebook MMS-TTS-VIE from Hugging Face
"""
import os
import io
import base64
import logging
import tempfile
from typing import Optional
import numpy as np

try:
    import torch
    import torchaudio
    from transformers import AutoProcessor, AutoModel
except ImportError:
    raise RuntimeError("Missing dependencies. Please install with: pip install transformers torch torchaudio")

# Logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("mms_tts")


class MMS_TTS_VIEService:
    def __init__(self):
        self.model = None
        self.processor = None
        self._initialized = False
        self.model_name = "facebook/mms-tts-vie"
        
    def _initialize_service(self):
        """Khởi tạo MMS-TTS-VIE model (lazy loading)"""
        if self._initialized:
            return
            
        try:
            logger.info("Initializing Facebook MMS-TTS-VIE model...")
            
            # Load processor and model
            self.processor = AutoProcessor.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name)
            
            # Move to GPU if available
            if torch.cuda.is_available():
                self.model = self.model.to("cuda")
                logger.info("Model loaded on GPU")
            else:
                logger.info("Model loaded on CPU")
            
            self._initialized = True
            logger.info(f"Facebook MMS-TTS-VIE model initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing MMS-TTS-VIE model: {str(e)}")
            raise
    
    def text_to_speech(self, text: str, max_length: int = 500) -> Optional[str]:
        """
        Chuyển đổi text thành audio sử dụng Facebook MMS-TTS-VIE
        
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
            
            # Tokenize text
            inputs = self.processor(text=text, return_tensors="pt")
            
            # Move inputs to same device as model
            if torch.cuda.is_available():
                inputs = {k: v.to("cuda") for k, v in inputs.items()}
            
            # Generate speech using the correct method
            logger.info(f"Generating speech for text: {text[:50]}...")
            with torch.no_grad():
                # Use the forward method to generate speech
                speech = self.model(**inputs).waveform
            
            # Convert to numpy array
            speech = speech.cpu().numpy().squeeze()
            
            # Normalize audio
            speech = speech / np.max(np.abs(speech)) * 0.9
            
            # Convert to WAV format
            audio_data = self._numpy_to_wav(speech, sample_rate=24000)
            
            # Convert to base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Trả về data URL cho WAV
            return f"data:audio/wav;base64,{audio_base64}"
                
        except Exception as e:
            logger.error(f"MMS-TTS-VIE error: {str(e)}")
            return None
    
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
        
        # Loại bỏ các ký tự đặc biệt có thể gây lỗi
        text = text.replace("<", "").replace(">", "").replace("&", "và")
        
        # Loại bỏ dấu xuống dòng liên tiếp
        text = " ".join(text.split())
        
        return text
    
    def _numpy_to_wav(self, audio_array: np.ndarray, sample_rate: int = 24000) -> bytes:
        """Chuyển đổi numpy array thành WAV bytes"""
        try:
            # Tạo temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Save as WAV using torchaudio
            torch_tensor = torch.from_numpy(audio_array).float()
            torchaudio.save(temp_path, torch_tensor.unsqueeze(0), sample_rate)
            
            # Read the file and return bytes
            with open(temp_path, 'rb') as f:
                audio_bytes = f.read()
            
            # Clean up temporary file
            os.unlink(temp_path)
            
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Error converting numpy to WAV: {str(e)}")
            raise
    
    def is_available(self) -> bool:
        """Kiểm tra xem MMS-TTS-VIE model có khả dụng không"""
        try:
            import transformers
            import torch
            return True
        except ImportError:
            return False
    
    def get_model_info(self) -> dict:
        """Lấy thông tin về model"""
        return {
            "name": "Facebook MMS-TTS-VIE",
            "model_id": self.model_name,
            "language": "Vietnamese",
            "sample_rate": 24000,
            "format": "WAV"
        }


# Singleton instance
mms_tts_service = MMS_TTS_VIEService()


def generate_audio_mms(text: str) -> Optional[str]:
    """
    Helper function để sinh audio từ text sử dụng MMS-TTS-VIE
    
    Args:
        text: Văn bản cần chuyển đổi
        
    Returns:
        Base64 encoded audio data URL hoặc None
    """
    return mms_tts_service.text_to_speech(text)


def is_mms_tts_available() -> bool:
    """Kiểm tra xem MMS-TTS-VIE có khả dụng không"""
    return mms_tts_service.is_available() 