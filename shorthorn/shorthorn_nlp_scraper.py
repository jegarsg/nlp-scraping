from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from tabulate import tabulate
from urllib.parse import urlencode
import time
import spacy

nlp = spacy.load("en_core_web_sm")

def extract_place_parts(command: str):
    doc = nlp(command)
    state = ""
    city = ""

    gpe_entities = [ent.text.strip() for ent in doc.ents if ent.label_ == "GPE"]

    lower_command = command.lower()
    if "city" in lower_command:
        try:
            parts = lower_command.split("city")
            for part in reversed(parts):
                tokens = part.strip().split()
                if tokens:
                    city = tokens[-1].title()
                    break
        except Exception:
            pass

    for ent in gpe_entities:
        ent_lower = ent.lower()
        if city and city.lower() in ent_lower:
            continue
        if not state:
            state = ent.title()

    return state.lower(), city.lower()


def extract_member_name(command: str):
    command_lower = command.lower()

    if "member name" in command_lower:
        after = command_lower.split("member name", 1)[1].strip()
        for loc_word in [" from ", " in ", " near ", " at "]:
            if loc_word in after:
                after = after.split(loc_word, 1)[0].strip()
        return after.strip(" '\"")

    doc = nlp(command)
    names = []
    current_name = []

    for token in doc:
        if token.ent_type_ in ("PERSON", "ORG"):
            current_name.append(token.text)
        else:
            if current_name:
                names.append(" ".join(current_name))
                current_name = []

    if current_name:
        names.append(" ".join(current_name))

    if names:
        return max(names, key=len)

    return ""



def clean_cell(cell):
    return cell.text.replace("\xa0", " ").strip()

def get_t_param(state: str, city: str, member_name: str, original_command: str) -> str:
    if any(keyword in original_command.lower() for keyword in ["all states", "nationwide", "entire country", "all us", "united states"]):
        return "897"
    if member_name and " " in member_name:
        return "901"
    if member_name and not state and not city:
        return "966"
    if city and not state and not member_name:
        return "978"
    if state and city:
        return "803"
    return "574"

def search_members_table(command: str):
    state, city = extract_place_parts(command)
    member_name = extract_member_name(command)

    if not state and not member_name and not city:
        if "all states" not in command.lower():
            print("⚠️ No recognizable input found (state, city, or member name).")
            return None

    if not state or "all states" in command.lower():
        state = "United States"

    print(f"🔍 Searching for members related to: {command}")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("https://shorthorn.digitalbeef.com")

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "search-member-location"))
        )

        select_element = Select(driver.find_element(By.ID, "search-member-location"))
        matched = False
        selected_value = ""

        for option in select_element.options:
            if state.lower() in option.text.lower():
                select_element.select_by_visible_text(option.text)
                selected_value = option.get_attribute("value")
                print(f"✅ Selected location: {option.text}")
                matched = True
                break

        if not matched:
            print(f"⚠️ No specific state match found. Falling back to 'United States'.")
            for option in select_element.options:
                if "united states" in option.text.lower():
                    select_element.select_by_visible_text(option.text)
                    selected_value = option.get_attribute("value")
                    print(f"🌎 Searching in state: {option.text}")
                    matched = True
                    break

        if not matched:
            print("❗ Error: Could not select a valid state.")
            return None

        if city:
            city_input = driver.find_element(By.ID, "ranch_search_city")
            city_input.clear()
            city_input.send_keys(city)
            print(f"🏙️ City: {city}")

        if member_name:
            name_input = driver.find_element(By.ID, "ranch_search_val")
            name_input.clear()
            name_input.send_keys(member_name)
            print(f"🧑 Member Name: {member_name}")

        driver.execute_script("doSearch_Ranch();")

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#dvSearchResults table table"))
        )
        time.sleep(1)

        t_param = get_t_param(state, city, member_name, command)

        base_url = "https://shorthorn.digitalbeef.com/modules/DigitalBeef-Landing/ajax/search_results_ranch.php"
        params = {
            "u": "",
            "p": "",
            "o": "0",
            "l": selected_value,
            "v": member_name.upper() if member_name else "",
            "herd_code": "",
            "ranch_id": "",
            "address_city": city.upper() if city else "",
            "address_email": "",
            "phone_number": "",
            "t": t_param
        }
        constructed_url = f"{base_url}?{urlencode(params)}"
        print(f"\n🔗 Constructed search URL:\n{constructed_url}")

        outer_div = driver.find_element(By.ID, "dvSearchResults")
        table = outer_div.find_element(By.CSS_SELECTOR, "table table")

        rows = table.find_elements(By.CSS_SELECTOR, "tr[id^='tr_']")
        if not rows:
            print("⚠️ No valid member rows found.")
            return constructed_url

        headers = ['Type', 'Member #', 'Prefix', 'Member Name', 'DBA', 'City', 'State/Prov']
        table_data = []

        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) >= 7:
                row_data = [clean_cell(cols[i]) for i in range(7)]
                table_data.append(row_data)

        if not table_data:
            print("ℹ️ No member records matched the search.")
            return constructed_url

        print(tabulate(table_data, headers=headers, tablefmt="github"))

        return constructed_url

    except Exception as e:
        print(f"❗ Error during scraping or processing: {str(e)}")
        return None
    finally:
        driver.quit()

if __name__ == "__main__":
    print("🌐 NLP Ranch Search (type 'exit' to quit)")
    while True:
        try:
            user_input = input("Enter search command: ").strip()
            if user_input.lower() in ('exit', 'quit'):
                print("👋 Goodbye!")
                break
            search_members_table(user_input)
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
