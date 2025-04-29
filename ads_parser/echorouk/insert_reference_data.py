# Import necessary libraries
from supabase import create_client, Client
import time

# Supabase credentials
SUPABASE_URL = "https://cpoinscesxsdisaueavm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNwb2luc2Nlc3hzZGlzYXVlYXZtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NTQ5MjI2OCwiZXhwIjoyMDYxMDY4MjY4fQ.s6BUPf1JKNURRY5c696UboY3EcPxALDosk7etd_WhXQ"

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Predefined lists
BUSINESS_LINES = [
    {"name": "Construction and Public Works"},
    {"name": "Information Technology and Software"},
    {"name": "Office Equipment and Stationery"},
    {"name": "Medical Equipment and Healthcare Services"},
    {"name": "Food Supplies and Catering"},
    {"name": "Transportation and Logistics"},
    {"name": "Security Services"},
    {"name": "Maintenance and Cleaning Services"},
    {"name": "Electrical Supplies and Services"},
    {"name": "Water and Sanitation Projects"},
    {"name": "Agricultural Supplies and Equipment"},
    {"name": "Energy and Renewable Energy"},
    {"name": "Consulting and Professional Services"},
    {"name": "Printing and Publishing Services"},
    {"name": "Laboratory and Scientific Equipment"},
    {"name": "Real Estate and Property Management"},
    {"name": "Automotive Supply and Maintenance"},
    {"name": "Telecommunication Services"},
    {"name": "Event Management and Advertising"},
    {"name": "Textiles and Uniform Supplies"}
]

WILAYAS = [
    {"name": "Adrar"},
    {"name": "Chlef"},
    {"name": "Laghouat"},
    {"name": "Oum El Bouaghi"},
    {"name": "Batna"},
    {"name": "Béjaïa"},
    {"name": "Biskra"},
    {"name": "Béchar"},
    {"name": "Blida"},
    {"name": "Bouira"},
    {"name": "Tamanrasset"},
    {"name": "Tébessa"},
    {"name": "Tlemcen"},
    {"name": "Tiaret"},
    {"name": "Tizi Ouzou"},
    {"name": "Algiers"},
    {"name": "Djelfa"},
    {"name": "Jijel"},
    {"name": "Sétif"},
    {"name": "Saïda"},
    {"name": "Skikda"},
    {"name": "Sidi Bel Abbès"},
    {"name": "Annaba"},
    {"name": "Guelma"},
    {"name": "Constantine"},
    {"name": "Médéa"},
    {"name": "Mostaganem"},
    {"name": "M'Sila"},
    {"name": "Mascara"},
    {"name": "Ouargla"},
    {"name": "Oran"},
    {"name": "El Bayadh"},
    {"name": "Illizi"},
    {"name": "Bordj Bou Arréridj"},
    {"name": "Boumerdès"},
    {"name": "El Tarf"},
    {"name": "Tindouf"},
    {"name": "Tissemsilt"},
    {"name": "El Oued"},
    {"name": "Khenchela"},
    {"name": "Souk Ahras"},
    {"name": "Tipaza"},
    {"name": "Mila"},
    {"name": "Aïn Defla"},
    {"name": "Naâma"},
    {"name": "Aïn Témouchent"},
    {"name": "Ghardaïa"},
    {"name": "Relizane"},
    {"name": "Timimoun"},
    {"name": "Bordj Badji Mokhtar"},
    {"name": "Ouled Djellal"},
    {"name": "Béni Abbès"},
    {"name": "In Salah"},
    {"name": "In Guezzam"},
    {"name": "Touggourt"},
    {"name": "Djanet"},
    {"name": "El M'Ghair"},
    {"name": "El Menia"}
]

ANNOUNCEMENT_TYPES = [
    {"name": "Tender"},
    {"name": "Request for Quotation (RFQ)"},
    {"name": "Award Notice"},
    {"name": "Prequalification Notice"},
    {"name": "Cancellation Notice"},
    {"name": "Recruitment Announcement"},
    {"name": "Sale or Auction Notice"},
    {"name": "Expression of Interest"},
    {"name": "Contract Amendment"},
    {"name": "General Information"}
]

def insert_reference_data():
    """Insert all reference data into the database."""
    
    # Insert business lines
    print("Inserting business lines...")
    success_count = 0
    for bl in BUSINESS_LINES:
        try:
            # Only insert the name, let the database generate the ID
            result = supabase.table("businessline").insert({"name": bl["name"]}).execute()
            if result.data:
                success_count += 1
                print(f"✅ Inserted business line: {bl['name']}")
            else:
                print(f"⚠️ Failed to insert business line: {bl['name']}")
        except Exception as e:
            print(f"❌ Error inserting business line {bl['name']}: {e}")
    
    print(f"Inserted {success_count}/{len(BUSINESS_LINES)} business lines")
    
    # Insert wilayas
    print("\nInserting wilayas...")
    success_count = 0
    for w in WILAYAS:
        try:
            # Note: The column name is 'wilaya_name' in the database
            result = supabase.table("wilaya").insert({"wilaya_name": w["name"]}).execute()
            if result.data:
                success_count += 1
                print(f"✅ Inserted wilaya: {w['name']}")
            else:
                print(f"⚠️ Failed to insert wilaya: {w['name']}")
        except Exception as e:
            print(f"❌ Error inserting wilaya {w['name']}: {e}")
    
    print(f"Inserted {success_count}/{len(WILAYAS)} wilayas")
    
    # Insert announcement types
    print("\nInserting announcement types...")
    success_count = 0
    for at in ANNOUNCEMENT_TYPES:
        try:
            result = supabase.table("announcementtype").insert({"name": at["name"]}).execute()
            if result.data:
                success_count += 1
                print(f"✅ Inserted announcement type: {at['name']}")
            else:
                print(f"⚠️ Failed to insert announcement type: {at['name']}")
        except Exception as e:
            print(f"❌ Error inserting announcement type {at['name']}: {e}")
    
    print(f"Inserted {success_count}/{len(ANNOUNCEMENT_TYPES)} announcement types")

if __name__ == "__main__":
    print("Starting reference data insertion...")
    start_time = time.time()
    
    try:
        insert_reference_data()
        print("\n✅ Reference data insertion completed successfully!")
    except Exception as e:
        print(f"\n❌ An error occurred during reference data insertion: {e}")
    
    end_time = time.time()
    print(f"Total execution time: {end_time - start_time:.2f} seconds")