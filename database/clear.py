import mysql.connector
import json
# Database connection
def create_connection():
    # Read JSON config document
    with open('selected_config.json', 'r') as file:
        config = json.load(file)  # Analyze JSON document
    
    # Make sure the JSON structure is correct
    required_keys = ["host", "database", "user", "password"]
    for key in required_keys:
        if key not in config or not config[key].strip():
            print(f"Error: '{key}' is missing or empty in selected_config.json")
            return None
    
    # Connect to database
    try:
        connection = mysql.connector.connect(
            host=config["host"],
            database=config["database"],
            user=config["user"],
            password=config["password"]
        )
        return connection  # Return the connection object
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None
# Clear all table information
def truncate_all_tables(connection):
    cursor = connection.cursor()
    
    # Forbid the Foreign Key Constraint
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
    
    
    cursor.execute(f"TRUNCATE TABLE `authors`;")
    cursor.execute(f"TRUNCATE TABLE `articles`;")
    cursor.execute(f"TRUNCATE TABLE `article_authors`;")
    
    
    
    # Use the Foreign Key Constraint
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
    connection.commit()
    print("All tables have been truncated.")

# Start
connection = create_connection()
if connection:
    truncate_all_tables(connection)
    connection.close()
