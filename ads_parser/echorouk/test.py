# Import necessary libraries
import google.generativeai as genai
from PIL import Image
import json
import re
from supabase import create_client, Client

# Configuration
API_KEY = "AIzaSyCB0c8HATyOGI0r14VQyQAPfVJdg06oTTo"  # Gemini API key
MODEL_NAME = "models/gemini-1.5-flash-latest"
IMAGE_PATH = r"ads_parser\echorouk\Fr_with_Pub-images-4.jpg.jpeg"

# Supabase credentials
SUPABASE_URL = "https://cpoinscesxsdisaueavm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNwb2luc2Nlc3hzZGlzYXVlYXZtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NTQ5MjI2OCwiZXhwIjoyMDYxMDY4MjY4fQ.s6BUPf1JKNURRY5c696UboY3EcPxALDosk7etd_WhXQ"  # use service_role key for insert permissions

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Predefined lists
BUSINESS_LINES = [
    {"id": 1, "name": "Construction and Public Works"},
    {"id": 2, "name": "Information Technology and Software"},
    {"id": 3, "name": "Office Equipment and Stationery"},
    {"id": 4, "name": "Medical Equipment and Healthcare Services"},
    {"id": 5, "name": "Food Supplies and Catering"},
    {"id": 6, "name": "Transportation and Logistics"},
    {"id": 7, "name": "Security Services"},
    {"id": 8, "name": "Maintenance and Cleaning Services"},
    {"id": 9, "name": "Electrical Supplies and Services"},
    {"id": 10, "name": "Water and Sanitation Projects"},
    {"id": 11, "name": "Agricultural Supplies and Equipment"},
    {"id": 12, "name": "Energy and Renewable Energy"},
    {"id": 13, "name": "Consulting and Professional Services"},
    {"id": 14, "name": "Printing and Publishing Services"},
    {"id": 15, "name": "Laboratory and Scientific Equipment"},
    {"id": 16, "name": "Real Estate and Property Management"},
    {"id": 17, "name": "Automotive Supply and Maintenance"},
    {"id": 18, "name": "Telecommunication Services"},
    {"id": 19, "name": "Event Management and Advertising"},
    {"id": 20, "name": "Textiles and Uniform Supplies"}
]

WILAYAS = [
    {"id": 1, "name": "Adrar"},
    {"id": 2, "name": "Chlef"},
    {"id": 3, "name": "Laghouat"},
    {"id": 4, "name": "Oum El Bouaghi"},
    {"id": 5, "name": "Batna"},
    {"id": 6, "name": "Béjaïa"},
    {"id": 7, "name": "Biskra"},
    {"id": 8, "name": "Béchar"},
    {"id": 9, "name": "Blida"},
    {"id": 10, "name": "Bouira"},
    {"id": 11, "name": "Tamanrasset"},
    {"id": 12, "name": "Tébessa"},
    {"id": 13, "name": "Tlemcen"},
    {"id": 14, "name": "Tiaret"},
    {"id": 15, "name": "Tizi Ouzou"},
    {"id": 16, "name": "Algiers"},
    {"id": 17, "name": "Djelfa"},
    {"id": 18, "name": "Jijel"},
    {"id": 19, "name": "Sétif"},
    {"id": 20, "name": "Saïda"},
    {"id": 21, "name": "Skikda"},
    {"id": 22, "name": "Sidi Bel Abbès"},
    {"id": 23, "name": "Annaba"},
    {"id": 24, "name": "Guelma"},
    {"id": 25, "name": "Constantine"},
    {"id": 26, "name": "Médéa"},
    {"id": 27, "name": "Mostaganem"},
    {"id": 28, "name": "M'Sila"},
    {"id": 29, "name": "Mascara"},
    {"id": 30, "name": "Ouargla"},
    {"id": 31, "name": "Oran"},
    {"id": 32, "name": "El Bayadh"},
    {"id": 33, "name": "Illizi"},
    {"id": 34, "name": "Bordj Bou Arréridj"},
    {"id": 35, "name": "Boumerdès"},
    {"id": 36, "name": "El Tarf"},
    {"id": 37, "name": "Tindouf"},
    {"id": 38, "name": "Tissemsilt"},
    {"id": 39, "name": "El Oued"},
    {"id": 40, "name": "Khenchela"},
    {"id": 41, "name": "Souk Ahras"},
    {"id": 42, "name": "Tipaza"},
    {"id": 43, "name": "Mila"},
    {"id": 44, "name": "Aïn Defla"},
    {"id": 45, "name": "Naâma"},
    {"id": 46, "name": "Aïn Témouchent"},
    {"id": 47, "name": "Ghardaïa"},
    {"id": 48, "name": "Relizane"},
    {"id": 49, "name": "Timimoun"},
    {"id": 50, "name": "Bordj Badji Mokhtar"},
    {"id": 51, "name": "Ouled Djellal"},
    {"id": 52, "name": "Béni Abbès"},
    {"id": 53, "name": "In Salah"},
    {"id": 54, "name": "In Guezzam"},
    {"id": 55, "name": "Touggourt"},
    {"id": 56, "name": "Djanet"},
    {"id": 57, "name": "El M'Ghair"},
    {"id": 58, "name": "El Menia"}
]


ANNOUNCEMENT_TYPES = [
    {"id": 1, "name": "Tender"},
    {"id": 2, "name": "Request for Quotation (RFQ)"},
    {"id": 3, "name": "Award Notice"},
    {"id": 4, "name": "Prequalification Notice"},
    {"id": 5, "name": "Cancellation Notice"},
    {"id": 6, "name": "Recruitment Announcement"},
    {"id": 7, "name": "Sale or Auction Notice"},
    {"id": 8, "name": "Expression of Interest"},
    {"id": 9, "name": "Contract Amendment"},
    {"id": 10, "name": "General Information"}
] 

# Initialize the Gemini API
genai.configure(api_key=API_KEY)

# System instruction
system_instruction = f"""
INPUT_IMAGE: {{image}}
PREDEFINED_LISTS:
BusinessLines = {BUSINESS_LINES}
Wilayas = {WILAYAS}
AnnouncementTypes = {ANNOUNCEMENT_TYPES}
"""

# Load the model
model = genai.GenerativeModel(
    model_name=MODEL_NAME,
    system_instruction=system_instruction
)

# Load image
def load_image(path: str) -> Image.Image:
    return Image.open(path)

image = load_image(IMAGE_PATH)

# Define prompt
prompt = """
Detect all announcements in INPUT_IMAGE.
For each announcement:
a. Compute its bounding box in pixel coordinates.
b. OCR the text and parse into fields:
   id, title, description, number, owner, terms, contact, dueAmount, publishDate, dueDate, status
c. Extract or infer the strings for Wilaya, Business Line, Announcement Type.
d. Case-insensitively match these strings against PREDEFINED_LISTS.
e. If match → insert the full object; if no match → create {id:null, name:original_string}.

Return a JSON array of announcement objects exactly matching this schema (no extra keys).
"""

# Generate content
response = model.generate_content(
    [prompt, image],
    stream=False
)

# Output the raw response
print(response.text)

# Clean response function
def clean_response_text(text):
    """
    Cleans the response text to extract a valid JSON string.
    """
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        return match.group(0)
    else:
        raise ValueError("No JSON array found in response.")

# Now: Parse and insert into Supabase
try:
    # First, fetch existing reference data from the database
    print("Fetching reference data from database...")
    
    # Get existing business lines
    business_lines_response = supabase.table("businessline").select("id,name").execute()
    db_business_lines = {item['name'].lower(): item['id'] for item in business_lines_response.data}
    
    # Get existing wilayas
    wilayas_response = supabase.table("wilaya").select("id,wilaya_name").execute()
    db_wilayas = {item['wilaya_name'].lower(): item['id'] for item in wilayas_response.data}
    
    # Get existing announcement types
    announcement_types_response = supabase.table("announcementtype").select("id,name").execute()
    db_announcement_types = {item['name'].lower(): item['id'] for item in announcement_types_response.data}
    
    print(f"Found {len(db_business_lines)} business lines, {len(db_wilayas)} wilayas, and {len(db_announcement_types)} announcement types")
    
    # Continue with the rest of the code
    clean_text = clean_response_text(response.text)
    announcements = json.loads(clean_text)

    for item in announcements:
        # Clean and convert dueAmount to a proper integer value
        due_amount = None
        if item.get("dueAmount"):
            # Remove currency symbols and non-numeric characters
            amount_str = str(item.get("dueAmount"))
            # Remove currency symbol and spaces
            amount_str = re.sub(r'[^\d,.]', '', amount_str)
            # Replace comma with dot for decimal point
            amount_str = amount_str.replace(',', '.')
            try:
                # Convert to integer instead of float
                due_amount = int(float(amount_str))
            except ValueError:
                due_amount = 0
        
        # Map the names to actual database IDs
        business_line_name = item["BusinessLine"].get("name", "").lower()
        business_line_id = db_business_lines.get(business_line_name)
        if not business_line_id:
            # Try to find a partial match
            for bl_name, bl_id in db_business_lines.items():
                if business_line_name in bl_name or bl_name in business_line_name:
                    business_line_id = bl_id
                    break
            if not business_line_id:
                business_line_id = next(iter(db_business_lines.values()), None)  # Default to first ID
        
        wilaya_name = item["Wilaya"].get("name", "").lower()
        wilaya_id = db_wilayas.get(wilaya_name)
        if not wilaya_id:
            # Try to find a partial match
            for w_name, w_id in db_wilayas.items():
                if wilaya_name in w_name or w_name in wilaya_name:
                    wilaya_id = w_id
                    break
            if not wilaya_id:
                wilaya_id = next(iter(db_wilayas.values()), None)  # Default to first ID
        
        announcement_type_name = item["AnnouncementType"].get("name", "").lower()
        announcement_type_id = db_announcement_types.get(announcement_type_name)
        if not announcement_type_id:
            # Try to find a partial match
            for at_name, at_id in db_announcement_types.items():
                if announcement_type_name in at_name or at_name in announcement_type_name:
                    announcement_type_id = at_id
                    break
            if not announcement_type_id:
                announcement_type_id = next(iter(db_announcement_types.values()), None)  # Default to first ID
        
        # Build the data to insert with default values for required fields
        data = {
            "title": item.get("title") or "Untitled Announcement",
            "description": item.get("description") or "No description provided",
            "number": item.get("number") or "N/A",
            "owner": item.get("owner") or "Unknown",
            "terms": item.get("terms") or "Standard terms apply",
            "contact": item.get("contact") or "No contact information",
            "dueamount": due_amount or 0,
            "publishdate": item.get("publishDate") or "2025-01-01",
            "duedate": item.get("dueDate") or "2025-12-31",
            "status": item.get("status") or 1,
            "wilayaid": wilaya_id,  # Use actual database ID
            "businesslineid": business_line_id,  # Use actual database ID
            "announcementtypeid": announcement_type_id,  # Use actual database ID
        }

        # Insert into Supabase
        response = supabase.table("announcement").insert(data).execute()

        # Check if insert successful
        if hasattr(response, "data") and response.data:
            print(f"✅ Inserted: {data['title']}")
        else:
            print(f"⚠️ Failed to insert: {data['title']}")

except Exception as e:
    print(f"❌ Error while parsing or inserting: {e}")
