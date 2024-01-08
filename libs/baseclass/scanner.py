from kivymd.app import MDApp
from kivy.uix.screenmanager import Screen
from kivy.lang.builder import Builder
from kivy.clock import Clock
from kivy.properties import ObjectProperty

from graph_generator import GraphGenerator
import numpy as np
import sqlite3
import datetime
import csv

from scipy.signal import savgol_filter

Builder.load_file('./libs/kv/scanner.kv')


class Scanner(Screen):
    id_save = ObjectProperty()
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    def on_enter(self, *args):

        self.conn = sqlite3.connect('spectral_calib.db')
        self.cursor = self.conn.cursor()
        # Create a table to store spectral data
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ReflectanceData (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                data BLOB NOT NULL
            )
        ''')

        # access the NIR
        self.spec = MDApp.get_running_app().spec

        mygraph = GraphGenerator()
        
        self.ids['rescan_button'].disabled = True
        self.ids['capture_button'].disabled = False

        self.figure_wgt4.figure = mygraph.fig
        self.figure_wgt4.axes = mygraph.ax1

        # get initial spectral data
        self.figure_wgt4.xmin= np.min(self.spec.wavelengths())
        self.figure_wgt4.xmax = np.max(self.spec.wavelengths())
        self.figure_wgt4.ymin= np.min(self.spec.intensities(False,True))
        self.figure_wgt4.ymax = np.max(self.spec.intensities(False,True))
        self.figure_wgt4.line1=mygraph.line1
        mygraph.line1.set_color('red')
        self.home()
        self.figure_wgt4.home()
       
        Clock.schedule_interval(self.update_graph,.1)

    def get_data(self, data_type):
        self.cursor.execute('''
            SELECT data FROM SpectralData WHERE type = ?
        ''', (data_type,))
        result = self.cursor.fetchone()
        if result:
            # Convert bytes back to NumPy array when retrieving from the database
            return np.frombuffer(result[0], dtype=np.float32)  # Adjust dtype based on your data type
        else:
            return None
    
    # rough estimation of available nitrogen
    def cal_nitrogen(self, organic_matter):
        return (((organic_matter/100) * 0.03) * 0.2) * 10000
        
    
    def reflectance_cal(self, sample_intensities):
        dark_data_retrieved = self.get_data('dark')
        light_data_retrieved = self.get_data('light')
        background_data_retrieved = self.get_data('background')

        ref_sub_dark = np.subtract(dark_data_retrieved, background_data_retrieved)
        corrected_ref = np.subtract(light_data_retrieved, ref_sub_dark)  

        sample_dark = np.subtract(dark_data_retrieved, background_data_retrieved)
        corrected_sample = np.subtract(sample_intensities, sample_dark)

        reflectance = np.divide(corrected_sample, corrected_ref)
        reflectance_mult = np.multiply(reflectance, 100)

        # Apply Savitzky-Golay filter
        window_length = 6  # Adjust for desired smoothing level
        polyorder = 3  # Polynomial order (often 2 or 3 for spectroscopy)

        return savgol_filter(reflectance_mult, window_length, polyorder)
    
    def set_touch_mode(self,mode):
        self.figure_wgt4.touch_mode=mode

    def home(self):
        self.figure_wgt4.home()
        
    def update_graph(self,_):
        xdata= self.spec.wavelengths()
        intensities = self.reflectance_cal(np.array(self.spec.intensities(False,True), dtype=np.float32))
        self.figure_wgt4.line1.set_data(xdata,intensities)
        self.figure_wgt4.ymax = np.max(intensities)
        self.figure_wgt4.ymin = np.min(intensities)
        self.figure_wgt4.xmax = np.max(xdata)
        self.figure_wgt4.xmin = np.min(xdata)
        self.home()
        self.figure_wgt4.figure.canvas.draw_idle()
        self.figure_wgt4.figure.canvas.flush_events() 
    
    def activate_button(self):
        self.ids['rescan_button'].disabled = not self.ids['rescan_button'].disabled
        self.ids['capture_button'].disabled = not self.ids['capture_button'].disabled
    
    def save_data(self, data_type, spectral_data):
        self.cursor.execute('''
            INSERT INTO ReflectanceData (type, data) VALUES (?, ?)
        ''', (data_type, spectral_data))
        last_inserted_id = self.cursor.lastrowid
        self.id_save.text = str(last_inserted_id)
        self.conn.commit()

    def disable_clock(self):
        self.save_data('reflectance', self.reflectance_cal(np.array(self.spec.intensities(False,True), dtype=np.float32)))
        Clock.unschedule(self.update_graph)


    def get_csv(self):
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


    def on_leave(self, *args):
        self.ids['rescan_button'].disabled = True
        self.ids['capture_button'].disabled = False
        self.conn.close()
        return super().on_leave(*args)
