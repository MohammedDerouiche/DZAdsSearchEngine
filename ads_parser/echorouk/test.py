# Import necessary libraries
import google.generativeai as genai
from PIL import Image
import json
from supabase import create_client, Client

# Configuration
API_KEY = "AIzaSyCB0c8HATyOGI0r14VQyQAPfVJdg06oTTo"  # Gemini API key
MODEL_NAME = "models/gemini-1.5-flash-latest"
IMAGE_PATH = r"ads_parser\echorouk\Screenshot_27-4-2025_194054_www.echoroukonline.com.jpeg"

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

# Create the system instruction dynamically
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

# Function to load an image
def load_image(path: str) -> Image.Image:
    """Load an image from a given path."""
    return Image.open(path)

# Load your input image
image = load_image(IMAGE_PATH)

# Define the prompt
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

OUTPUT FORMAT EXAMPLE:
[
  {
    "announcement": {
      "id": "announcement_1",
      "title": "Tender for Office Supplies",
      "description": "Supply of standard office stationery …",
      "number": "TDR-2025-01",
      "owner": "Regional Directorate of Education",
      "terms": null,
      "contact": "Procurement Office, …",
      "dueAmount": null,
      "publishDate": "2025-04-23",
      "dueDate": "2025-05-10",
      "status": 1
    },
    "wilaya": {"id": 2, "name": "wilaya_name2"},
    "businessLine": {"id": null, "name": "Office Stationery Supply"},
    "announcementType": {"id": 1, "name": "announcement_type1"},
    "boundingBox": {"x_min": 60, "y_min": 200, "x_max": 480, "y_max": 550}
  }
]
"""

# Generate content
response = model.generate_content(
    [prompt, image],
    stream=False
)

# Output the response text
print(response.text)

# Now: Parse the response and insert into Supabase
try:
    announcements = json.loads(response.text)  # Parse the JSON output

    for item in announcements:
        # Prepare data for insertion
        data_to_insert = {
            "announcement_id": item["announcement"]["id"],
            "title": item["announcement"]["title"],
            "description": item["announcement"]["description"],
            "number": item["announcement"]["number"],
            "owner": item["announcement"]["owner"],
            "terms": item["announcement"]["terms"],
            "contact": item["announcement"]["contact"],
            "due_amount": item["announcement"]["dueAmount"],
            "publish_date": item["announcement"]["publishDate"],
            "due_date": item["announcement"]["dueDate"],
            "status": item["announcement"]["status"],
            "wilaya_id": item["wilaya"]["id"],
            "wilaya_name": item["wilaya"]["name"],
            "business_line_id": item["businessLine"]["id"],
            "business_line_name": item["businessLine"]["name"],
            "announcement_type_id": item["announcementType"]["id"],
            "announcement_type_name": item["announcementType"]["name"],
            "bounding_box": json.dumps(item["boundingBox"])  # Save as JSON string
        }

        # Insert into your Supabase table (example table name: "announcements")
        res = supabase.table("announcements").insert(data_to_insert).execute()

        # Check the result
        if res.status_code == 201:
            print(f"Inserted announcement: {data_to_insert['title']}")
        else:
            print(f"Failed to insert: {res.data}")

except Exception as e:
    print(f"Error parsing or inserting: {e}")
