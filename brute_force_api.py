
import asyncio
from bot.services.remnawave import api

async def main():
    base_endpoint = "hwid/devices"
    
    # Params to test for LIMIT/SIZE
    limit_params = ["limit", "take", "count", "size", "per_page", "pageSize", "max"]
    
    # Params to test for PAGINATION
    page_params = ["page", "p", "offset", "skip", "pageIndex", "cursor", "after"]
    
    # Params to test for FILTERING
    filter_params = ["userUuid", "userId", "uuid", "search", "q", "query", "filter"]
    
    user_uuid = "a402ad1d-e982-48b7-b4a4-784c14d07892"
    
    print("--- Brute Forcing Params ---")
    
    # 1. Limit Check (Pass limit=2 to see if result count changes)
    print("Checking LIMIT params (expecting 2 results)...")
    for p in limit_params:
        url = f"{base_endpoint}?{p}=2"
        try:
            res = await api._request("GET", url)
            count = 0
            if res and 'response' in res:
                count = len(res['response'].get('devices', []))
            print(f"{p}=2 -> Got {count}")
            if count == 2:
                print(f"!!! SUCCESS: {p} works for limit!")
        except: pass
        
    # 2. Pagination Check (Pass limit (if found) or default, and page params)
    # If we assume limit is ignored (25 returned), we try to get page 2.
    # To detect page 2, we need the first item of page 1.
    print("Fetching Page 1 baseline...")
    baseline_hwid = None
    try:
        res = await api._request("GET", base_endpoint)
        if res and 'response' in res:
            baseline_hwid = res['response']['devices'][0]['hwid']
    except: pass
    
    print(f"Baseline HWID: {baseline_hwid}")
    
    if baseline_hwid:
        print("Checking PAGINATION params (expecting different HWID)...")
        for p in page_params:
            val = 1 if p in ["page", "p", "pageIndex"] else 25 # offset 25
            url = f"{base_endpoint}?{p}={val}"
            try:
                res = await api._request("GET", url)
                if res and 'response' in res:
                    devs = res['response'].get('devices', [])
                    if devs:
                        first = devs[0]['hwid']
                        if first != baseline_hwid:
                             print(f"!!! SUCCESS: {p}={val} changed results!")
                        else:
                             print(f"{p}={val} -> Same")
            except: pass

    # 3. Filter Check
    print("Checking FILTER params (expecting 0 or 5 results)...")
    for p in filter_params:
        url = f"{base_endpoint}?{p}={user_uuid}"
        try:
            res = await api._request("GET", url)
            count = 0
            if res and 'response' in res:
                 devs = res['response'].get('devices', [])
                 matches = [d for d in devs if d.get('userUuid') == user_uuid]
                 count = len(matches)
            print(f"{p}={user_uuid} -> Matched: {count} / Fetched: {len(devs)}")
            if count > 0:
                print(f"!!! SUCCESS: {p} works for filtering!")
        except: pass

if __name__ == "__main__":
    asyncio.run(main())
