"""
Test user stats isolation - verify different users have independent stats
"""
import pytest
from uuid import uuid4


class TestUserStatsIsolation:
    """Test that stats are properly isolated between users"""
    
    @pytest.fixture
    def base_url(self):
        return "http://localhost:8000"
    
    @pytest.fixture
    def character_id(self):
        # 煤球的ID
        return "a7b8c9d0-e1f2-4a3b-5c6d-7e8f9a0b1c2d"

    @pytest.mark.asyncio
    async def test_new_user_starts_with_zero_stats(self, base_url, character_id):
        """New user should have 0 messages, 0 gifts, etc."""
        import httpx
        
        new_user_id = f"new-user-{uuid4().hex[:8]}"
        
        async with httpx.AsyncClient() as client:
            # Get stats for brand new user
            resp = await client.get(
                f"{base_url}/api/v1/characters/{character_id}/stats",
                headers={"X-User-ID": new_user_id}
            )
            
            assert resp.status_code == 200
            data = resp.json()
            
            # New user should have all zeros
            assert data["total_messages"] == 0, f"Expected 0 messages, got {data['total_messages']}"
            assert data["total_gifts"] == 0
            assert data["streak_days"] == 0
            print(f"✅ New user {new_user_id} has zero stats")

    @pytest.mark.asyncio
    async def test_user_stats_are_isolated(self, base_url, character_id):
        """User A's messages should not affect User B's stats"""
        import httpx
        
        user_a_id = f"test-user-a-{uuid4().hex[:8]}"
        user_b_id = f"test-user-b-{uuid4().hex[:8]}"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Create session for User A
            create_resp = await client.post(
                f"{base_url}/api/v1/chat/sessions",
                json={"character_id": character_id},
                headers={"X-User-ID": user_a_id}
            )
            assert create_resp.status_code == 200, f"Create session failed: {create_resp.text}"
            session_a = create_resp.json()["session_id"]
            
            # User A sends a message
            resp_a = await client.post(
                f"{base_url}/api/v1/chat/completions",
                json={
                    "session_id": session_a,
                    "message": "你好，测试消息",
                },
                headers={"X-User-ID": user_a_id}
            )
            assert resp_a.status_code == 200, f"User A send failed: {resp_a.text}"
            
            # Check User A's stats (should be >= 1)
            stats_a = await client.get(
                f"{base_url}/api/v1/characters/{character_id}/stats",
                headers={"X-User-ID": user_a_id}
            )
            assert stats_a.status_code == 200
            data_a = stats_a.json()
            assert data_a["total_messages"] >= 1, f"User A should have at least 1 message, got {data_a['total_messages']}"
            print(f"✅ User A has {data_a['total_messages']} messages")
            
            # Check User B's stats (should still be 0)
            stats_b = await client.get(
                f"{base_url}/api/v1/characters/{character_id}/stats",
                headers={"X-User-ID": user_b_id}
            )
            assert stats_b.status_code == 200
            data_b = stats_b.json()
            assert data_b["total_messages"] == 0, f"User B should have 0 messages, got {data_b['total_messages']}"
            print(f"✅ User B correctly has 0 messages (isolated from User A)")

    @pytest.mark.asyncio
    async def test_delete_only_affects_own_user(self, base_url, character_id):
        """Deleting User A's data should not affect User B"""
        import httpx
        
        user_a = f"delete-test-a-{uuid4().hex[:8]}"
        user_b = f"delete-test-b-{uuid4().hex[:8]}"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Create sessions for both users
            sess_a_resp = await client.post(
                f"{base_url}/api/v1/chat/sessions",
                json={"character_id": character_id},
                headers={"X-User-ID": user_a}
            )
            session_a = sess_a_resp.json()["session_id"]
            
            sess_b_resp = await client.post(
                f"{base_url}/api/v1/chat/sessions",
                json={"character_id": character_id},
                headers={"X-User-ID": user_b}
            )
            session_b = sess_b_resp.json()["session_id"]
            
            # Both users send messages
            await client.post(
                f"{base_url}/api/v1/chat/completions",
                json={"session_id": session_a, "message": "User A message"},
                headers={"X-User-ID": user_a}
            )
            await client.post(
                f"{base_url}/api/v1/chat/completions",
                json={"session_id": session_b, "message": "User B message"},
                headers={"X-User-ID": user_b}
            )
            
            # Verify both have messages
            stats_a_before = await client.get(
                f"{base_url}/api/v1/characters/{character_id}/stats",
                headers={"X-User-ID": user_a}
            )
            stats_b_before = await client.get(
                f"{base_url}/api/v1/characters/{character_id}/stats",
                headers={"X-User-ID": user_b}
            )
            assert stats_a_before.json()["total_messages"] >= 1, "User A should have messages before delete"
            assert stats_b_before.json()["total_messages"] >= 1, "User B should have messages before delete"
            print(f"✅ Before delete: User A={stats_a_before.json()['total_messages']}, User B={stats_b_before.json()['total_messages']}")
            
            # Delete User A's data
            delete_resp = await client.delete(
                f"{base_url}/api/v1/characters/{character_id}/user-data",
                headers={"X-User-ID": user_a}
            )
            assert delete_resp.status_code == 200, f"Delete failed: {delete_resp.text}"
            print(f"✅ Deleted User A's data: {delete_resp.json()}")
            
            # User A should now have 0
            stats_a_after = await client.get(
                f"{base_url}/api/v1/characters/{character_id}/stats",
                headers={"X-User-ID": user_a}
            )
            assert stats_a_after.json()["total_messages"] == 0, f"User A stats should be reset to 0, got {stats_a_after.json()['total_messages']}"
            print(f"✅ User A now has 0 messages (correctly reset)")
            
            # User B should still have their messages
            stats_b_after = await client.get(
                f"{base_url}/api/v1/characters/{character_id}/stats",
                headers={"X-User-ID": user_b}
            )
            assert stats_b_after.json()["total_messages"] >= 1, f"User B stats should be unchanged, got {stats_b_after.json()['total_messages']}"
            print(f"✅ User B still has {stats_b_after.json()['total_messages']} messages (unaffected)")

    @pytest.mark.asyncio
    async def test_stats_count_increments_correctly(self, base_url, character_id):
        """Stats total_messages should increment with each message"""
        import httpx
        
        test_user = f"count-test-{uuid4().hex[:8]}"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Create session
            sess_resp = await client.post(
                f"{base_url}/api/v1/chat/sessions",
                json={"character_id": character_id},
                headers={"X-User-ID": test_user}
            )
            session_id = sess_resp.json()["session_id"]
            
            # Send 3 messages
            for i in range(3):
                resp = await client.post(
                    f"{base_url}/api/v1/chat/completions",
                    json={"session_id": session_id, "message": f"Test message {i+1}"},
                    headers={"X-User-ID": test_user}
                )
                assert resp.status_code == 200, f"Message {i+1} failed: {resp.text}"
            
            # Check stats
            stats = await client.get(
                f"{base_url}/api/v1/characters/{character_id}/stats",
                headers={"X-User-ID": test_user}
            )
            data = stats.json()
            
            # Should have exactly 3 messages recorded
            assert data["total_messages"] == 3, f"Expected 3 messages, got {data['total_messages']}"
            print(f"✅ Stats correctly shows 3 messages")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
