import mysql.connector
import json
import dotenv
import os

dotenv.load_dotenv()

file_path = './gas_stations.json'
with open(file_path, 'r', encoding='utf-8') as file:
    scraped_data = json.load(file)

# Setup your database connection
db_connection = mysql.connector.connect(
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME')
)
cursor = db_connection.cursor()

# Delete all records for operator_id = 3 
# delete_query = "DELETE FROM gas_stations WHERE operator_id = %s"
# cursor.execute(delete_query, (3,))
# db_connection.commit()

# Begin transaction
db_connection.start_transaction()

if isinstance(scraped_data, list): 
    for station in scraped_data:  
        city = station['city']
        municipality_name = city.split(" - ")[-1]
        
        municipality_query = "SELECT municipality_id, province_id FROM Municipalities WHERE municipality_name = %s"
        cursor.execute(municipality_query, (municipality_name,))
        municipality_result = cursor.fetchone()
        
        if not municipality_result:
            province_name = city.split(" - ")[-1]  
            cursor.execute("SELECT province_id FROM Provinces WHERE province_name = %s", (province_name,))
            province_result = cursor.fetchone()
            if province_result:
                province_id = province_result[0]
            else:
                province_id = None
            
            insert_municipality_query = """
                INSERT INTO Municipalities (municipality_name, province_id)
                VALUES (%s, %s)
            """
            cursor.execute(insert_municipality_query, (municipality_name, province_id))
            db_connection.commit()
            
            municipality_id = cursor.lastrowid
        else:
            municipality_id, province_id = municipality_result

        country_id = 1
        
        insert_query = """
            INSERT INTO gas_stations (station_name, address, latitude, longitude, municipality_id, operator_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            station['name'],  
            station['address'], 
            station['latitude'],  
            station['longitude'],  
            municipality_id, 
            3
        ))
        db_connection.commit()

db_connection.commit()
cursor.close()
db_connection.close()
