import urllib.request
import urllib.error
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def make_request(method, endpoint, data=None, token=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    req_body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=req_body, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            content_type = response.info().get_content_type()
            body = response.read().decode()
            
            if "application/json" in content_type:
                return {"status": status, "data": json.loads(body) if body else None}
            else:
                return {"status": status, "data": body} # Return raw string for CSV etc
    except urllib.error.HTTPError as e:
        status = e.getcode()
        try:
            body = e.read().decode()
            return {"status": status, "data": json.loads(body)}
        except:
            return {"status": status, "error": "Non-JSON error response"}
    except Exception as e:
        return {"status": 500, "error": str(e)}

print("\n" + "="*60)
print("   FINTRACK END-TO-END VERIFICATION (PUBLIC-FIRST MODE)")
print("="*60)

time.sleep(1)

# 1. PUBLIC ACCESS
print("\n[STEP 1] Verifying Public Access (No Token)...")
res1 = make_request("GET", "/analytics/summary")
print(f"  [PASS] Public Summary" if res1["status"] == 200 else f"  [FAIL] Public Summary: {res1}")

new_tx = {"amount": 10.0, "type": "expense", "category": "other", "date": "2026-04-05", "notes": "E2E"}
res2 = make_request("POST", "/transactions", data=new_tx)
recorded_id = None
if res2["status"] == 201:
    recorded_id = res2["data"]["data"]["id"]
    print(f"  [PASS] Public Create Transaction (ID: {recorded_id})")
else:
    print(f"  [FAIL] Public Create: {res2}")

# 2. SECURITY
print("\n[STEP 2] Verifying Restricted Actions...")
res3 = make_request("DELETE", f"/transactions/{recorded_id}")
print(f"  [PASS] Public Delete Blocked (Status {res3['status']})" if res3["status"] in (401, 403) else f"  [FAIL] Public Delete: {res3}")

# 3. ADMIN
print("\n[STEP 3] Verifying Admin Access...")
login = make_request("POST", "/auth/login", data={"email": "admin@demo.com", "password": "Admin1234"})
admin_token = login["data"]["data"]["access_token"] if login["status"] == 200 else None
if admin_token:
    print("  [PASS] Admin Login")
    res4 = make_request("DELETE", f"/transactions/{recorded_id}", token=admin_token)
    print("  [PASS] Admin Delete" if res4["status"] == 204 else f"  [FAIL] Admin Delete: {res4}")
else:
    print(f"  [FAIL] Admin Login: {login}")

# 4. EXPORT
print("\n[STEP 4] Verifying Export (Public)...")
res5 = make_request("GET", "/transactions/export?format=csv")
if res5["status"] == 200 and "id,user_id,amount" in res5["data"]:
    print("  [PASS] Public CSV Export")
else:
    print(f"  [FAIL] Public Export: {res5}")

print("\n" + "="*60)
print("   VERIFICATION COMPLETE")
print("="*60 + "\n")
