import spacy
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from tabulate import tabulate
import traceback
import time
import re
import difflib

nlp = spacy.load("en_core_web_sm")

breed_map = {
    "(AK) - Ameri-Kiko": "12",
    "(AC) - American Black": "9",
    "(AB) - American Boer": "10",
    "(AD) - American Dapple": "13",
    "(AM) - American Myotonic": "11",
    "(AR) - American Red": "1",
    "(AS) - American Savanna": "8",
    "(AP) - American Spanish": "14",
    "(B) - Boer": "3",
    "(C) - Composite": "4",
    "(K) - Kiko": "5",
    "(M) - Myotonic": "6",
    "(A) - Savanna": "2",
    "(SP) - Spanish": "7"
}

def parse_command(command):
    doc = nlp(command)

    state = None
    member = None
    breed_name = None

    for ent in doc.ents:
        if ent.label_ == "GPE":
            state = ent.text
            break

    for ent in doc.ents:
        if ent.label_ == "PERSON":
            member = ent.text
            break
    
    if not member:
        match = re.search(r"\b([A-Z][a-z]+)'s\b", command)
        if match:
            member_candidate = match.group(1).strip()
            if len(member_candidate) > 2:
                member = member_candidate
                print(f"🔎 Found possessive member name: {member} (partial)")


    breed_pattern = re.search(r"\(([A-Z]{1,2})\)\s*-\s*([a-z\s]+)", command, re.IGNORECASE)
    if breed_pattern:
        breed_name = f"({breed_pattern.group(1).upper()}) - {breed_pattern.group(2).title()}"
    else:
        command_text = command.lower()
        for key in breed_map.keys():
            breed_only = key.split(" - ")[1].lower()
            if breed_only in command_text:
                breed_name = key
                break

    if "all breeders" in command.lower() and ("all states" in command.lower() or "from all" in command.lower() or "everywhere" in command.lower()):
        return {"state": None, "breed_name": None, "member": None}

    return {
        "state": state,
        "breed_name": breed_name,
        "member": member
    }


def extract_table_data(driver, expected_member_name=None):
    print("⏳ Waiting for results table to load...")
    wait = WebDriverWait(driver, 10)
    all_data = []

    simplified_expected = None
    if expected_member_name:
        simplified_expected = re.sub(r"[^a-z]", "", expected_member_name.lower())

    while True:
        try:
            table = wait.until(EC.presence_of_element_located((By.ID, "example")))
            tbody = table.find_element(By.TAG_NAME, "tbody")
            rows = tbody.find_elements(By.TAG_NAME, "tr")

            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 6:
                    state = cells[1].text.strip()
                    name = cells[2].text.strip()
                    farm = cells[3].text.strip()
                    phone = cells[4].text.strip()
                    website = cells[5].text.strip()

                    if simplified_expected:
                        expected_words = re.findall(r"[a-z]+", simplified_expected)
                        simplified_name = re.sub(r"[^a-z]", "", name.lower())

                        if not any(word in simplified_name for word in expected_words) and not any(simplified_name in word for word in expected_words):
                            continue


                    all_data.append([state, name, farm, phone, website])

            next_btn = driver.find_element(By.ID, "example_next")
            next_class = next_btn.get_attribute("class")

            if "disabled" in next_class:
                print("🛑 Reached the last page.")
                break
            else:
                print("➡️ Moving to next page...")
                next_btn.click()
                time.sleep(1)

        except Exception as e:
            print("❌ Error during pagination:")
            traceback.print_exc()
            break

    print("\n📄 AMGR Directory Results:\n")
    if all_data:
        print(tabulate(all_data, headers=["State", "Name", "Farm", "Phone", "Website"], tablefmt="fancy_grid"))
    else:
        print("⚠️ No results found for the given member name.")

    return all_data


def select_by_value(select_element, value):
    if not value:
        select_element.select_by_index(0)
        return
    for option in select_element.options:
        if option.get_attribute('value') == value:
            select_element.select_by_value(value)
            print(f"✅ Selected by value: {option.text} (value: {value})")
            return
    print(f"⚠️ Value '{value}' not found in options. Selecting first option.")
    select_element.select_by_index(0)

def select_option_by_text(select_element, target_text):
    target_text_lower = target_text.strip().lower()

    for option in select_element.options:
        if option.text.strip().lower() == target_text_lower:
            select_element.select_by_visible_text(option.text)
            print(f"✅ Selected option by exact match: '{option.text}'")
            return True

    for option in select_element.options:
        if target_text_lower in option.text.strip().lower():
            select_element.select_by_visible_text(option.text)
            print(f"✅ Selected option by partial match: '{option.text}'")
            return True
    print(f"⚠️ Could not find option matching '{target_text}'. Selecting first option.")
    select_element.select_by_index(0)
    return False

def find_best_member_match(member_partial, scrape_results):
    if not member_partial or not scrape_results:
        return None
    names = [row["Name"] if isinstance(row, dict) else row for row in scrape_results if row]
    matches = difflib.get_close_matches(member_partial, names, n=1, cutoff=0.6)
    return matches[0] if matches else None

def scrape_amgr_directory(state="", breed_name=None, member_name=None):
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless")

    driver = None

    try:
        print("🚀 Launching browser...")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        wait = WebDriverWait(driver, 15)

        print("🌐 Navigating to AMGR directory...")
        url = "https://www.amgr.org/frm_directorySearch.cfm"
        driver.get(url)
        time.sleep(2)

        print("🧪 Checking if page has iframe...")
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if len(iframes) > 0:
            driver.switch_to.frame(iframes[0])

        print(f"📍 Selecting state: {state if state else '[ALL STATES]'}")
        state_dropdown_el = wait.until(EC.presence_of_element_located((By.NAME, "stateID")))
        state_dropdown = Select(state_dropdown_el)

        if state:
            select_option_by_text(state_dropdown, state)
        else:
            state_dropdown.select_by_index(0)

        print(f"👤 Selecting member: {member_name if member_name else '[ALL MEMBERS]'}")
        member_dropdown_el = wait.until(EC.presence_of_element_located((By.NAME, "memberID")))
        member_dropdown = Select(member_dropdown_el)

        def clean_name(name):
            return re.sub(r"\b(farm|farms|breeder|breeders|in|from)\b", "", name.lower()).strip()

        if member_name:
            simplified_input = clean_name(member_name)
            matched = False
            matching_members = []

            for option in member_dropdown.options:
                option_text = option.text.strip()
                cleaned_option = clean_name(option_text)

                if simplified_input in cleaned_option or cleaned_option in simplified_input:
                    matching_members.append(option_text)


            if len(matching_members) == 1:
                member_dropdown.select_by_visible_text(matching_members[0])
                print(f"✅ Selected member: '{matching_members[0]}'")
                matched = True
            elif len(matching_members) > 1:
                print(f"⚠️ Found multiple similar members for '{member_name}':")
                for match in matching_members:
                    print(f"   → {match}")
                print("ℹ️ Please specify the full member name more precisely.")
                member_dropdown.select_by_index(0)
            else:
                print(f"⚠️ Could not find member '{member_name}'. Selecting all.")
                member_dropdown.select_by_index(0)


        print("🐐 Selecting breed...")
        breed_dropdown_el = wait.until(EC.presence_of_element_located((By.NAME, "breedID")))
        breed_dropdown = Select(breed_dropdown_el)

        breed_id = None
        if breed_name:
            breed_id = breed_map.get(breed_name)
            if breed_id:
                print(f"🔍 Interpreted breed: {breed_name} -> breedID = {breed_id}")
            else:
                print(f"⚠️ Breed '{breed_name}' not found in breed_map.")
        else:
            print("ℹ️ No breed specified; selecting all.")

        select_by_value(breed_dropdown, breed_id)

        print("🔘 Submitting the form...")
        submit_btn = wait.until(EC.element_to_be_clickable((By.ID, "submitButton")))
        submit_btn.click()

        time.sleep(2)
        return extract_table_data(driver, expected_member_name=member_name)



    except Exception as e:
        print("❌ Error during scraping:")
        traceback.print_exc()
        if driver:
            with open("page_debug.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)

    finally:
        if driver:
            print("🧹 Closing browser...")
            driver.quit()

if __name__ == "__main__":
    print("🔎 Welcome to the AMGR NLP Scraper!")

    while True:
        command = input("\n🗣️  Enter your request (or type 'exit' to quit): ").strip()

        if command.lower() in ["exit", "quit", "q"]:
            print("👋 Exiting scraper. Goodbye!")
            break

        parsed = parse_command(command) or {}
        state = parsed.get("state")
        breed_name = parsed.get("breed_name")
        print(f"Interpreted: State = {state}, Breed = {breed_name}")

        member_name = None

        match = re.search(r"(?:member\s+name|member)\s+([a-zA-Z\s]+?)(?:\s+from|\s+in|$)", command, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            candidate_lower = candidate.lower()
            if state:
                candidate_lower = re.sub(rf"\b{re.escape(state.lower())}\b", "", candidate_lower)

            breed_only = ""
            if breed_name and " - " in breed_name:
                breed_only = breed_name.split(" - ")[1].lower()
                candidate_lower = re.sub(rf"\b{re.escape(breed_only)}\b", "", candidate_lower)

            generic_words = ['all', 'breeders', 'breeder', 'farm', 'farms', 'in', 'from', 'state', 'states', 'members', 'member']
            for gw in generic_words:
                candidate_lower = re.sub(rf"\b{gw}\b", "", candidate_lower)

            cleaned_candidate = " ".join(candidate_lower.split()).strip()

            if cleaned_candidate and len(cleaned_candidate) >= 3:
                member_name = cleaned_candidate.title()
                print(f"Detected member name: '{member_name}'")
            else:
                print("ℹ️ No valid member name detected after cleaning; searching all members.")
                member_name = None
        else:
            print("ℹ️ No member name detected; searching all members.")

        results = scrape_amgr_directory(state=state, breed_name=breed_name, member_name=member_name)

        if member_name and results:
            dict_results = []
            for r in results:
                if len(r) >= 2:
                    dict_results.append({"Name": r[1]})

            best_match = find_best_member_match(member_name, dict_results)
            if best_match:
                print(f"\n🎯 Best matching member full name found: {best_match}")
            else:
                print("\n⚠️ Could not find a close match for the member name in results.")