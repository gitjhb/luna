"""
Tests for Cold War Unlock via Apology Gift

Test scenarios:
1. User in cold war cannot chat normally (gets "..." response)
2. Sending apology gift unlocks cold war
3. After unlock, user can chat normally again
4. Non-apology gifts do NOT unlock cold war
"""

import pytest
import asyncio
from datetime import datetime
from uuid import uuid4

# Test configuration
TEST_USER_ID = "test-user-123"
TEST_CHARACTER_ID = "test-char-456"


async def ensure_user_has_credits(user_id: str, amount: int = 500):
    """Ensure test user has enough credits"""
    from app.services.payment_service import payment_service
    wallet = await payment_service.get_wallet(user_id)
    if wallet["total_credits"] < amount:
        # Add credits
        await payment_service.add_credits(user_id, amount, "test_topup")


class TestColdWarUnlock:
    """Test cold war unlock via apology gift"""
    
    @pytest.fixture
    def emotion_score_service(self):
        """Get emotion score service instance"""
        from app.services.emotion_score_service import emotion_score_service
        return emotion_score_service
    
    @pytest.fixture
    def gift_service(self):
        """Get gift service instance"""
        from app.services.gift_service import gift_service
        return gift_service
    
    @pytest.mark.asyncio
    async def test_user_enters_cold_war_when_score_below_threshold(self, emotion_score_service):
        """Test: Score <= -75 triggers cold war state"""
        # Reset first
        await emotion_score_service.reset_score(TEST_USER_ID, TEST_CHARACTER_ID)
        
        # Reduce score to cold war threshold
        await emotion_score_service.update_score(
            TEST_USER_ID, TEST_CHARACTER_ID, 
            delta=-80, 
            reason="test_offense"
        )
        
        # Check cold war state
        data = await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
        
        assert data["score"] <= -75, f"Score should be <= -75, got {data['score']}"
        assert data["in_cold_war"] == True, "Should be in cold war"
    
    @pytest.mark.asyncio
    async def test_cold_war_blocks_normal_chat(self, emotion_score_service):
        """Test: Cold war state should be detectable for chat blocking"""
        # Setup cold war
        await emotion_score_service.reset_score(TEST_USER_ID, TEST_CHARACTER_ID)
        await emotion_score_service.update_score(
            TEST_USER_ID, TEST_CHARACTER_ID,
            delta=-80,
            reason="test_offense"
        )
        
        data = await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
        
        # Verify cold war is active
        is_cold_war = data.get("in_cold_war", False) or data.get("score", 0) <= -75
        assert is_cold_war, "Cold war should be active"
    
    @pytest.mark.asyncio
    async def test_apology_gift_unlocks_cold_war(self, emotion_score_service, gift_service):
        """Test: Sending apology gift should unlock cold war"""
        # Ensure user has credits
        await ensure_user_has_credits(TEST_USER_ID, 500)
        
        # Setup cold war
        await emotion_score_service.reset_score(TEST_USER_ID, TEST_CHARACTER_ID)
        await emotion_score_service.update_score(
            TEST_USER_ID, TEST_CHARACTER_ID,
            delta=-80,
            reason="test_offense"
        )
        
        # Verify in cold war
        data = await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
        assert data["in_cold_war"] == True, "Should be in cold war before gift"
        
        # Send apology gift
        result = await gift_service.send_apology_gift(
            user_id=TEST_USER_ID,
            character_id=TEST_CHARACTER_ID,
            gift_id="apology_bouquet"  # Apology gift
        )
        
        assert result["success"] == True, f"Gift should succeed: {result}"
        assert result.get("cold_war_unlocked") == True, "Should unlock cold war"
        
        # Verify cold war is unlocked
        data = await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
        assert data["in_cold_war"] == False, "Cold war should be unlocked"
        assert data["score"] > -75, f"Score should be above cold war threshold, got {data['score']}"
    
    @pytest.mark.asyncio
    async def test_normal_gift_does_not_unlock_cold_war(self, emotion_score_service, gift_service):
        """Test: Normal (non-apology) gifts should NOT unlock cold war"""
        # Ensure user has credits
        await ensure_user_has_credits(TEST_USER_ID, 500)
        
        # Setup cold war
        await emotion_score_service.reset_score(TEST_USER_ID, TEST_CHARACTER_ID)
        await emotion_score_service.update_score(
            TEST_USER_ID, TEST_CHARACTER_ID,
            delta=-80,
            reason="test_offense"
        )
        
        # Send normal gift (rose is not an apology gift)
        result = await gift_service.send_gift(
            user_id=TEST_USER_ID,
            character_id=TEST_CHARACTER_ID,
            gift_type="rose",  # Normal gift, not apology
            idempotency_key=str(uuid4()),
        )
        
        # Gift may succeed but should NOT unlock cold war
        data = await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
        
        # Cold war should still be active (score may improve slightly but not unlock)
        is_still_cold = data.get("in_cold_war", False) or data.get("score", 0) <= -75
        assert is_still_cold, "Normal gift should NOT fully unlock cold war"
    
    @pytest.mark.asyncio
    async def test_after_unlock_chat_works_normally(self, emotion_score_service):
        """Test: After unlocking, emotion state should allow normal chat"""
        # Reset to neutral
        await emotion_score_service.reset_score(TEST_USER_ID, TEST_CHARACTER_ID)
        
        data = await emotion_score_service.get_score(TEST_USER_ID, TEST_CHARACTER_ID)
        
        assert data["in_cold_war"] == False, "Should not be in cold war"
        assert data["score"] >= -75, "Score should be above cold war threshold"
        assert data["state"] == "neutral", f"State should be neutral, got {data['state']}"


# Run tests directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
