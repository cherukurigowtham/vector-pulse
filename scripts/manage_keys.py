import requests
import sys
import os
import json

# Simple CLI for Vector-Pulse API Key Management
# Requires a running API server and an admin session/token

BASE_URL = os.getenv("VECTOR_PULSE_URL", "http://localhost:8000/v1/security/auth")

def get_headers():
    token = os.getenv("VP_SESSION_TOKEN")
    if not token:
        print("Error: VP_SESSION_TOKEN environment variable not set.")
        sys.exit(1)
    return {"Cookie": f"vp_token={token}"}

def list_keys():
    print("Listing keys...")
    resp = requests.get(f"{BASE_URL}/keys", headers=get_headers())
    if resp.status_code == 200:
        print(json.dumps(resp.json(), indent=2))
    else:
        print(f"Error: {resp.status_code} - {resp.text}")

def create_key(name="New Key"):
    print(f"Creating key: {name}...")
    resp = requests.post(f"{BASE_URL}/keys", headers=get_headers(), json={"name": name})
    if resp.status_code == 200:
        print("Key created successfully!")
        print(json.dumps(resp.json(), indent=2))
    else:
        print(f"Error: {resp.status_code} - {resp.text}")

def revoke_key(key_hash):
    print(f"Revoking key: {key_hash}...")
    resp = requests.delete(f"{BASE_URL}/keys/{key_hash}", headers=get_headers())
    if resp.status_code == 200:
        print("Key revoked successfully.")
    else:
        print(f"Error: {resp.status_code} - {resp.text}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 manage_keys.py [list|create|revoke] [args...]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "list":
        list_keys()
    elif cmd == "create":
        name = sys.argv[2] if len(sys.argv) > 2 else "New Key"
        create_key(name)
    elif cmd == "revoke":
        if len(sys.argv) < 3:
            print("Usage: python3 manage_keys.py revoke [key_hash]")
            sys.exit(1)
        revoke_key(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}")

if __name__ == "__main__":
    main()
