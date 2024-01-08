import sqlite3
import csv
import numpy as np
import datetime

# Get the current date and time
current_datetime = datetime.datetime.now()

# Format it as mm/dd/yyyy_time
formatted_datetime = current_datetime.strftime("%m_%d_%Y_%H:%M:%S")


# Connect to the SQLite database
conn = sqlite3.connect('spectral_calib.db')
cursor = conn.cursor()

# Fetch all data from the ReflectanceData table
cursor.execute("SELECT * FROM ReflectanceData")
data = cursor.fetchall()

# Define the path for the CSV file
csv_file_path = f"reflectance{(formatted_datetime)}.csv"

# Write the data to the CSV file
with open(csv_file_path, 'w', newline='') as csv_file:
    csv_writer = csv.writer(csv_file)
    
    # Write the header (column names)
    column_names = [description[0] for description in cursor.description]
    csv_writer.writerow(column_names)
    
    # Write the data rows, including the BLOB data
    for row in data:
        row_data = list(row)
        
        # Convert the BLOB data to a list of 97 float numbers
        blob_data = np.frombuffer(row_data[-1], dtype=np.float32)

        row_data.pop(-1) 
        
        
        row_data.extend(blob_data)
        print(row_data)
        # Remove the last element which is the BLOB data
        # row_data.pop(-1)  # Corrected from row_data.pop(1) to row_data.pop(-1)
        
        csv_writer.writerow(row_data)

# Close the database connection
conn.close()

print(f"Data from the ReflectanceData table, including BLOB data, has been saved to {csv_file_path}.")
