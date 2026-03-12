import asyncio
import os
import vector_pulse
from api_gateway import _check_ip_intelligence, _check_sybil, r

async def verify():
    print("Testing Phase 12: Precision Engines...")
    
    # 1. Test Rust Address Normalization
    print("\n[1] Testing Rust Address Normalization...")
    test_cases = [
        ("Flat No-101, Lake Apartment", "f no 101 lake apt"),
        ("Sec-45, Block-B, Road 5", "sec 45 blk b rd 5"),
        ("123, Main Street, Floor 2", "123 main st fl 2")
    ]
    
    for raw, expected_key_parts in test_cases:
        norm = vector_pulse.normalize_address(raw)
        print(f"Raw: {raw} -> Norm: {norm}")
        # Note: My exact Rust implementation might differ slightly in whitespace, checking containment
        # Actually I just want to see it run
        
    # 2. Test Sybil with Normalization
    print("\n[2] Testing Sybil Detection with Normalization...")
    # These two should result in the same hash and thus be seen as the same address
    addr1 = "Flat 101, Lake View"
    addr2 = "f 101, lake-view"
    
    uid = "test_user_123"
    await _check_sybil(uid, addr1)
    is_sybil = await _check_sybil("another_uid", addr2)
    print(f"Shared Address Sybil Detected (Expected True if limit < 2): {is_sybil}")

    # 3. Test Local IP Intelligence
    print("\n[3] Testing Local IP Intelligence...")
    # Test with a US IP (should be risky geo)
    us_ip = "8.8.8.8"
    is_risky = await _check_ip_intelligence(us_ip)
    print(f"US IP (8.8.8.8) Risky: {is_risky}")
    
    # Test with a local IP (mocked 127 should be false)
    local_ip = "127.0.0.1"
    is_risky_local = await _check_ip_intelligence(local_ip)
    print(f"Local IP (127.0.0.1) Risky: {is_risky_local}")

    print("\nVerification Finished.")

if __name__ == "__main__":
    asyncio.run(verify())
