import time
from amgr_nlp_scraper import parse_command, scrape_amgr_directory

test_cases = [
    {
        "input": "Show all American Savanna breeders",
        "expected": {
             "state": None,
            "breed_name": "(AS) - American Savanna",
            "member": None
        }
    },
    {
        "input": "Show all breeders in Texas",
        "expected": {
            "state": "Texas",
            "breed_name": None,
            "member": None
        }
    },
    {
        "input": "Show John Hurlbert farm in Alabama",
        "expected": {
            "state": "Alabama",
            "breed_name": None,
            "member": "John Hurlbert"
        }
    },
    {
        "input": "Show Savanna breeders in Texas",
        "expected": {
            "state": "Texas",
            "breed_name": "(A) - Savanna",
            "member": None
        }
    },
    {
        "input": "Show all members in Colorado",
        "expected": {
            "state": "Colorado",
            "breed_name": None,
            "member": None
        }
    }
]

def run_tests():
    print("=== Running NLP Parsing & Scraper Tests ===\n")
    for idx, test_case in enumerate(test_cases, 1):
        command = test_case["input"]
        expected = test_case["expected"]

        # Measure parse_command time
        start_time = time.time()
        actual = parse_command(command)
        parse_duration = time.time() - start_time

        print(f"Test Case {idx}: {command}")
        print(f"Expected: {expected}")
        print(f"Actual:   {actual}")
        print(f"⏱️ parse_command execution time: {parse_duration:.6f} seconds")

        if actual == expected:
            print("✅ PASSED")
        else:
            print("❌ FAILED")

    
        params = {
            "state": actual.get("state"),
            "breed_name": actual.get("breed_name"),
        }
        params = {k: v for k, v in params.items() if v is not None}

        start_scrape = time.time()
        results = scrape_amgr_directory(**params)
        scrape_duration = time.time() - start_scrape

        print(f"⏱️ scrape_amgr_directory execution time: {scrape_duration:.2f} seconds")
        print(f"Scrape Results Count: {len(results)}")
        print("-" * 60)

if __name__ == "__main__":
    run_tests()
