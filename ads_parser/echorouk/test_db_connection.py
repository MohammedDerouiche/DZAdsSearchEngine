# Import necessary libraries
from supabase import create_client, Client
import json
from datetime import datetime

# Supabase credentials
SUPABASE_URL = "https://cpoinscesxsdisaueavm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNwb2luc2Nlc3hzZGlzYXVlYXZtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NTQ5MjI2OCwiZXhwIjoyMDYxMDY4MjY4fQ.s6BUPf1JKNURRY5c696UboY3EcPxALDosk7etd_WhXQ"

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Sample announcement data
sample_announcements = [
    {
        "announcement": {
            "id": "test_announcement_1",
            "title": "Supply of Medical Equipment",
            "description": "Tender for the supply of medical equipment for the regional hospital",
            "number": "MED-2025-001",
            "owner": "Ministry of Health",
            "terms": "Payment within 30 days of delivery",
            "contact": "procurement@health.gov.dz, Tel: +213 123456789",
            "dueamount": 5000000,
            "publishdate": "2025-04-25",
            "duedate": "2025-05-15",
            "status": 1,
            "wilayaid": 16,
            "businesslineid": 4,
            "announcementtypeid": 1
        },
        "wilaya": {"id": 16, "name": "Algiers"},
        "businessLine": {"id": 4, "name": "Medical Equipment and Healthcare Services"},
        "announcementType": {"id": 1, "name": "Tender"},
        "boundingBox": {"x_min": 100, "y_min": 200, "x_max": 500, "y_max": 600}
    },
    {
        "announcement": {
            "id": "test_announcement_2",
            "title": "Construction of School Building",
            "description": "Tender for the construction of a new primary school in Oran",
            "number": "CON-2025-042",
            "owner": "Ministry of Education",
            "terms": "Completion within 12 months",
            "contact": "projects@education.gov.dz",
            "dueamount": 25000000,
            "publishdate": "2025-04-26",
            "duedate": "2025-05-20",
            "status": 1,
            "wilayaid": 31,
            "businesslineid": 1,
            "announcementtypeid": 1
        },
        "wilaya": {"id": 31, "name": "Oran"},
        "businessLine": {"id": 1, "name": "Construction and Public Works"},
        "announcementType": {"id": 1, "name": "Tender"},
        "boundingBox": {"x_min": 150, "y_min": 250, "x_max": 550, "y_max": 650}
    }
]

def test_database_connection():
    """Test the connection to the Supabase database."""
    try:
        # Simple query to check connection
        response = supabase.table("announcement").select("*").limit(1).execute()
        print(f"Database connection successful. Status code: {response.status_code}")
        print(f"Data: {response.data}")
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

def insert_sample_data():
    """Insert sample announcement data into the database."""
    print("\n--- Inserting Sample Data ---")
    
    for i, item in enumerate(sample_announcements):
        try:
            # 1. Insert announcement data
            announcement_data = {
                "title": item["announcement"]["title"],
                "description": item["announcement"]["description"],
                "number": item["announcement"]["number"],
                "owner": item["announcement"]["owner"],
                "terms": item["announcement"]["terms"],
                "contact": item["announcement"]["contact"],
                "dueamount": item["announcement"]["dueamount"],
                "publishdate": item["announcement"]["publishdate"],
                "duedate": item["announcement"]["duedate"],
                "status": item["announcement"]["status"],
                "wilayaid": item["announcement"]["wilayaid"],
                "businesslineid": item["announcement"]["businesslineid"],
                "announcementtypeid": item["announcement"]["announcementtypeid"]
            }
            
            print(f"\nInserting announcement {i+1}: {announcement_data['title']}")
            
            # Insert into the announcement table
            announcement_res = supabase.table("announcement").insert(announcement_data).execute()
            
            if hasattr(announcement_res, 'data') and announcement_res.data:
                announcement_id = announcement_res.data[0]['id']
                print(f"Successfully inserted announcement with ID: {announcement_id}")
                
                # 2. Insert announcement image data
                image_data = {
                    "announcementid": announcement_id,
                    "imagepath": f"sample_image_{i+1}.jpg"
                }
                
                image_res = supabase.table("announcementimage").insert(image_data).execute()
                
                if hasattr(image_res, 'data') and image_res.data:
                    print(f"Successfully inserted image for announcement {announcement_id}")
                else:
                    print(f"Failed to insert image for announcement {announcement_id}")
            else:
                print(f"Failed to insert announcement. Response: {announcement_res}")
                
        except Exception as e:
            print(f"Error inserting announcement {i+1}: {e}")
            import traceback
            traceback.print_exc()

def check_database_structure():
    """Check the structure of the database tables."""
    try:
        print("\n--- Checking Database Structure ---")
        
        # List of tables to check
        tables = ["announcement", "wilaya", "businessline", "announcementtype", "announcementimage"]
        
        for table in tables:
            try:
                response = supabase.table(table).select("*").limit(1).execute()
                print(f"Table '{table}' exists and is accessible")
                
                if hasattr(response, 'data') and response.data:
                    print(f"  Sample data: {response.data}")
                else:
                    print(f"  No data in table")
                    
            except Exception as e:
                print(f"Error accessing table '{table}': {e}")
        
    except Exception as e:
        print(f"Error checking database structure: {e}")

if __name__ == "__main__":
    print("=== Supabase Connection Test ===")
    
    try:
        # Test database connection
        if test_database_connection():
            # Check database structure
            check_database_structure()
            
            # Ask user if they want to insert sample data
            user_input = input("\nDo you want to insert sample data into the database? (y/n): ")
            
            if user_input.lower() == 'y':
                insert_sample_data()
            else:
                print("Sample data insertion skipped.")
        else:
            print("Database connection test failed. Please check your credentials and network connection.")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()