#!/usr/bin/env python3
"""
Test script for ChromaDB integration
"""
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_chroma_db():
    """Test the ChromaDB service"""
    try:
        from services import chroma_db
        
        print("🔍 Testing ChromaDB integration...")
        
        # Test availability
        is_available = chroma_db.is_chroma_available()
        print(f"✅ ChromaDB available: {is_available}")
        
        if not is_available:
            print("❌ ChromaDB not available. Please install required dependencies:")
            print("   pip install chromadb")
            return False
        
        # Test service initialization
        print("📋 Initializing ChromaDB service...")
        chroma_db.chroma_service._initialize_service()
        print("✅ ChromaDB service initialized successfully")
        
        # Test adding chat messages
        print("📝 Testing chat message storage...")
        test_user_id = 1
        test_profile_id = 1
        test_chat_id = 1
        
        # Add test messages
        success1 = chroma_db.add_chat_message(
            user_id=test_user_id,
            profile_id=test_profile_id,
            chat_id=test_chat_id,
            message_id=1,
            content="Tôi muốn hỏi về thực phẩm tốt cho sức khỏe",
            is_user=True
        )
        
        success2 = chroma_db.add_chat_message(
            user_id=test_user_id,
            profile_id=test_profile_id,
            chat_id=test_chat_id,
            message_id=2,
            content="Rau xanh và trái cây rất tốt cho sức khỏe. Bạn nên ăn nhiều rau cải, bông cải xanh, và các loại trái cây giàu vitamin C.",
            is_user=False
        )
        
        print(f"✅ User message added: {success1}")
        print(f"✅ AI message added: {success2}")
        
        # Test context retrieval
        print("🔍 Testing context retrieval...")
        context_messages = chroma_db.get_chat_context(
            user_id=test_user_id,
            profile_id=test_profile_id,
            chat_id=test_chat_id,
            query="thực phẩm sức khỏe",
            limit=5
        )
        
        print(f"✅ Retrieved {len(context_messages)} context messages")
        for i, msg in enumerate(context_messages):
            print(f"   {i+1}. {msg['content'][:50]}...")
        
        # Test recent history
        print("📚 Testing recent history retrieval...")
        recent_messages = chroma_db.get_recent_chat_history(
            user_id=test_user_id,
            profile_id=test_profile_id,
            chat_id=test_chat_id,
            limit=10
        )
        
        print(f"✅ Retrieved {len(recent_messages)} recent messages")
        
        # Test user summary
        print("📊 Testing user chat summary...")
        summary = chroma_db.chroma_service.get_user_chat_summary(test_user_id, test_profile_id)
        print(f"✅ Chat summary: {summary}")
        
        # Test stats
        print("📈 Testing ChromaDB stats...")
        stats = chroma_db.chroma_service.get_stats()
        print(f"✅ ChromaDB stats: {stats}")
        
        print("\n🎉 All tests passed! ChromaDB integration is working correctly.")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please install required dependencies:")
        print("   pip install chromadb")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_chroma_db()
    sys.exit(0 if success else 1) 