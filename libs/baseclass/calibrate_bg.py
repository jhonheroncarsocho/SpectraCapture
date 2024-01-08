from kivymd.app import MDApp
from kivy.uix.screenmanager import Screen
from kivy.lang.builder import Builder
from kivy.clock import Clock
from kivy.properties import ObjectProperty

from graph_generator import GraphGenerator
import numpy as np
import sqlite3


Builder.load_file('./libs/kv/calibrate_bg.kv')


class CalibrateBG(Screen):
    figure_wgt2 = ObjectProperty()
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    def on_enter(self, *args):
        self.conn = sqlite3.connect('spectral_calib.db')
        self.cursor = self.conn.cursor()
        # Create a table to store spectral data
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS SpectralData (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                data BLOB NOT NULL
            )
        ''')

        # access the NIR
        # self.spec = MDApp.get_running_app().spec

        mygraph = GraphGenerator()
        
        self.figure_wgt2.figure = mygraph.fig
        self.figure_wgt2.axes = mygraph.ax1

        # get initial spectral data
        self.figure_wgt2.xmin= 0 #np.min(self.spec.wavelengths())
        self.figure_wgt2.xmax = 100 #np.max(self.spec.wavelengths())
        self.figure_wgt2.ymin= 0 #np.min(self.spec.intensities(False,True))
        self.figure_wgt2.ymax = 100 #np.max(self.spec.intensities(False,True))
        self.figure_wgt2.line1=mygraph.line1
        mygraph.line1.set_color('red')
        self.home()
        self.figure_wgt2.home()

        
       
        Clock.schedule_interval(self.update_graph,.1)
    
    # Function to delete existing data of a certain type
    def delete_data(self):
        self.cursor.execute('''
            DELETE FROM SpectralData WHERE type = ?
        ''', ("background",))
        self.conn.commit()

    # Function to insert data into the table
    def insert_data(self, data_type, spectral_data):
        self.delete_data()
        self.cursor.execute('''
            INSERT INTO SpectralData (type, data) VALUES (?, ?)
        ''', (data_type, spectral_data))
        self.conn.commit()

    def set_touch_mode(self,mode):
        self.figure_wgt2.touch_mode=mode

    def home(self):
        self.figure_wgt2.home()
        
    def update_graph(self,_):
        xdata= np.random.randint(0, 100, size=(1, 92)) #self.spec.wavelengths()
        intensities = np.random.randint(0, 100, size=(1, 92)) #self.spec.intensities(False,True)
        self.figure_wgt2.line1.set_data(xdata,intensities)
        self.figure_wgt2.ymax = np.max(intensities)
        self.figure_wgt2.ymin = np.min(intensities)
        self.figure_wgt2.xmax = np.max(xdata)
        self.figure_wgt2.xmin = np.min(xdata)
        self.home()
        self.figure_wgt2.figure.canvas.draw_idle()
        self.figure_wgt2.figure.canvas.flush_events() 
    
    def activate_capture(self):
        self.ids['capture_bg'].disabled = not self.ids['capture_bg'].disabled
        self.ids['next_bg'].disabled = not self.ids['next_bg'].disabled
        self.ids['rescan_bg'].disabled = not self.ids['rescan_bg'].disabled
    
    def activate_rescan(self):
        self.ids['rescan_bg'].disabled = not self.ids['rescan_bg'].disabled
        self.ids['next_bg'].disabled = not self.ids['next_bg'].disabled
        self.ids['capture_bg'].disabled = not self.ids['capture_bg'].disabled

    def disable_clock(self):
        self.insert_data('background', np.random.randint(0, 100, size=(1, 92))) #np.array(self.spec.intensities(False,True), dtype=np.float32).reshape(-1, 1))
        Clock.unschedule(self.update_graph)
    
    def on_leave(self, *args):
        self.ids['next_bg'].disabled = True
        self.ids['capture_bg'].disabled = False
        self.ids['rescan_bg'].disabled = True
        self.conn.close()
        return super().on_leave(*args)