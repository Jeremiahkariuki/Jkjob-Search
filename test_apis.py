"""
Diagnostic script with SSL context using certifi.
"""
import ssl
import time
import urllib.request
import certifi

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 (Jkjob-search/2.0)"
ssl_context = ssl.create_default_context(cafile=certifi.where())

def test_endpoint(name: str, url: str):
    start = time.time()
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
        )
        with urllib.request.urlopen(req, context=ssl_context, timeout=10) as response:
            latency = time.time() - start
            data = response.read()
            status = response.status
            size_kb = len(data) / 1024
            print(f"[✓] {name:<25} Status: {status} | Size: {size_kb:.1f} KB | Time: {latency:.2f}s")
            return True, data
    except Exception as e:
        latency = time.time() - start
        print(f"[✗] {name:<25} FAILED: {e} | Time: {latency:.2f}s")
        return False, None

def main():
    print("=" * 70)
    print("TESTING ALL LIVE APIS & JOB SOURCES WITH CERTIFI SSL CONTEXT")
    print("=" * 70)

    # 1. Standard Job APIs
    print("\n--- 1. Standard Remote Job APIs ---")
    test_endpoint("Remotive API", "https://remotive.com/api/remote-jobs?category=software-dev&limit=10")
    test_endpoint("Arbeitnow API", "https://www.arbeitnow.com/api/job-board-api")
    test_endpoint("Jobicy API", "https://jobicy.com/api/v2/remote-jobs?count=10&tag=engineering")

    # 2. RSS Feeds
    print("\n--- 2. RSS Feeds ---")
    test_endpoint("WeWorkRemotely RSS", "https://weworkremotely.com/categories/remote-programming-jobs.rss")

    # 3. Developer Platforms
    print("\n--- 3. Developer Feeds ---")
    test_endpoint("Himalayas API", "https://himalayas.app/jobs/api?limit=10")
    test_endpoint("RemoteOK API", "https://remoteok.com/api?tag=dev")

    # 4. Direct ATS Boards
    print("\n--- 4. Direct ATS Endpoints ---")
    test_endpoint("Canonical (Greenhouse)", "https://boards-api.greenhouse.io/v1/boards/canonical/jobs")
    test_endpoint("GiveDirectly (Greenhouse)", "https://boards-api.greenhouse.io/v1/boards/givedirectly/jobs")
    test_endpoint("Alpaca (Greenhouse)", "https://boards-api.greenhouse.io/v1/boards/alpaca/jobs")
    test_endpoint("Bboxx (Lever)", "https://api.lever.co/v0/postings/bboxx?mode=json")
    test_endpoint("Ona (Lever)", "https://api.lever.co/v0/postings/ona?mode=json")
    test_endpoint("Cellulant (Lever)", "https://api.lever.co/v0/postings/cellulant?mode=json")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
