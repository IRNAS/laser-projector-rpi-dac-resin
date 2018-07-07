"""
   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import io
import time
import threading
import random
import remi.gui as gui
from remi.gui import *
from remi import start, App
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import RandomPointGenerator as rp
import numpy as np
import matplotlib.pyplot as plt
from threading import Thread
import sys
import csv
from ad5721 import AD5721
import RPi.GPIO as GPIO

N = 2**16 # Range of laser motion
laser = 29 # Define laser
START = 0 # Start laser motion
LOCK = 0 # Lock movement and points buttons when generating path and moving laser
PAUSE = 0 # Pause on/off
STEP = 1000 # Initial movement step
SPEED = 0.005 # laser speed
MOVE_T = 60 # Move interval in secons
PAUSE_T = 60 # Pause interval in seconds
plot_data = [N/2, N/2] # Current laser position - half of movement range

# Define point arrays
PX = [] # Paths
PY = []

startT = time.time() # Time when laser motion starts



# Plot image GUI
class MatplotImage(gui.Image):
    ax = None

    def __init__(self, **kwargs):
        super(MatplotImage, self).__init__("/%s/get_image_data?update_index=0" % id(self), **kwargs)
        self._buf = None
        self._buflock = threading.Lock()
        self._fig = Figure(figsize=(7, 7))
        self.ax = self._fig.add_subplot(111)
        self.ax.set_xlim(0,N)
        self.ax.set_ylim(0,N)
        self.redraw()

    def redraw(self):
        canv = FigureCanvasAgg(self._fig)
        buf = io.BytesIO()
        canv.print_figure(buf, format='png')
        with self._buflock:
            if self._buf is not None:
                self._buf.close()
            self._buf = buf

        i = int(time.time() * 1e6)
        self.attributes['src'] = "/%s/get_image_data?update_index=%d" % (id(self), i)

        super(MatplotImage, self).redraw()

    def get_image_data(self, update_index):
        with self._buflock:
            if self._buf is None:
                return None
            self._buf.seek(0)
            data = self._buf.read()

        return [data, {'Content-type': 'image/png'}]

# APP
class MyApp(App):

    def __init__(self, *args):
        super(MyApp, self).__init__(*args)

    def main(self):

        # App variables
        self.points_x = [] # Corner points x coordinates
        self.points_y = [] # Corner points y coordinates
        self.contour_x = [] # Contour points
        self.contour_y = []

        # Main widget===================================================================================================
        wid = Widget(width=600, height=500, margin='0px auto', style="position: relative")

        # Body==========================================================================================================
        # ==============================================================================================================
        wid_body = HBox(width='100%', height='100%', style='position: absolute; left: 0px; top: 0px')
        wid.append(wid_body)

        # Plot and data variables=======================================================================================
        plotContainer = VBox(width='65%', height='100%', style='position: absolute; left: 0px; top: 0px')
        wid_body.append(plotContainer)

        #  Head and instructions
        wid_head = VBox(width='100%', height='20%', style='position: absolute; align: left; left: 0px; top: 0px')
        plotContainer.append(wid_head)

        appTitleContainer = HBox(width='100%', height='50%', style='position: absolute; align: left; left: 0px; top: 0px')
        wid_head.append(appTitleContainer)
        appTitle = gui.Label("LASERSKI SISTEM ZA ODGANJANJE GOLOBOV",style='left:10%; top:20%')
        appTitleContainer.append(appTitle)

        # Instructions - help
        InstrContainer = HBox(width='100%', height='50%', style='position: absolute; align: left; left: 0px; top: 0px')
        wid_head.append(InstrContainer)

        btInstr = gui.Button('Instructions', width='20%', height='70%')
        #btInstr.style['margin'] = '5%'
        btInstr.set_on_click_listener(self.on_button_pressed_instr)
        InstrContainer.append(btInstr)

        btContour = gui.Button('Contour', width='20%', height='70%')
        #btContour.style['margin'] = '5%'
        btContour.set_on_click_listener(self.on_button_pressed_contour)
        InstrContainer.append(btContour)

        btLoad = gui.Button('Load last path', width='20%', height='70%')
        #btContour.style['margin'] = '5%'
        btLoad.set_on_click_listener(self.on_button_pressed_load)
        InstrContainer.append(btLoad)

        btOn = gui.Button('On', width='10%', height='70%')
        #btOn.style['margin'] = '5%'
        btOn.set_on_click_listener(self.on_button_pressed_on)
        InstrContainer.append(btOn)

        btOff = gui.Button('Off', width='10%', height='70%')
        #btOff.style['margin'] = '5%'
        btOff.set_on_click_listener(self.on_button_pressed_off)
        InstrContainer.append(btOff)

        # Plot
        self.mpl = MatplotImage(width='100%', height='90%')
        self.mpl.style['margin'] = '0px'
        self.mpl.ax.set_title("test")
        self.sc_poly = self.mpl.ax.plot(self.points_x, self.points_y, c='r')
        self.scp = self.mpl.ax.scatter(self.points_x, self.points_y, c='r')
        self.mpl.redraw()
        plotContainer.append(self.mpl)

        # Movement Buttons==============================================================================================

        # CONTINERS:
        # Main buttons container
        btContainer = VBox(width='35%', height='100%', style='position: absolute; left: 0px; top: 0px')
        wid_body.append(btContainer)

        # Arrow buttons container
        btContainerArrows = VBox(width='100%', height='30%', style='position: absolute; left: 0px; top: 0px')
        btContainer.append(btContainerArrows)

        # Up button container
        btContainerArrowsUp = HBox(width='100%', height='33%', style='position: absolute; left: 0px; top: 0px')
        btContainerArrows.append(btContainerArrowsUp)

        # Left and right buttons container
        btContainerArrowsLR = HBox(width='100%', height='34%', style='position: absolute; left: 0px; top: 60px')
        btContainerArrows.append(btContainerArrowsLR)

        # Down button container
        btContainerArrowsDown = HBox(width='100%', height='33%', style='position: absolute; left: 0px; top: 120px')
        btContainerArrows.append(btContainerArrowsDown)

        # BUTTONS:
        # Up
        btUp = gui.Button('Up', width='25%', height='70%')
        btUp.style['margin'] = '10%'
        btUp.set_on_click_listener(self.on_button_pressed_up)

        # Down
        btDown = gui.Button('Down', width='25%', height='70%')
        btUp.style['margin'] = '10%'
        btDown.set_on_click_listener(self.on_button_pressed_down)

        # Right
        btRight = gui.Button('Right', width='25%', height='70%')
        btUp.style['margin'] = '10%'
        btRight.set_on_click_listener(self.on_button_pressed_right)

        # Left
        btLeft = gui.Button('Left', width='25%', height='70%')
        btUp.style['margin'] = '10%'
        btLeft.set_on_click_listener(self.on_button_pressed_left)

        # Append to containers
        btContainerArrowsUp.append(btUp)
        btContainerArrowsDown.append(btDown)
        btContainerArrowsLR.append(btLeft)
        btContainerArrowsLR.append(btRight)

        # Steps and speed===============================================================================================
        # CONTAINERS:
        # Main slider container
        btContainerSliders = VBox(width='100%', height='40%', style='position: absolute; left: 0px; top: 0px')
        btContainer.append(btContainerSliders)

        # Step size slider container
        btContainerStepSize = VBox(width='100%', height='30%', style='position: absolute; left: 0px; top: 0px')
        btContainerSliders.append(btContainerStepSize)

        # Speed slider container
        btContainerSpeedSlider = VBox(width='100%', height='30%', style='position: absolute; left: 0px; top: 0px')
        btContainerSliders.append(btContainerSpeedSlider)

        # Move and pause time
        btContainerTime = HBox(width='100%', height='40%', style='position: absolute; left: 0px; top: 0px')
        btContainerSliders.append(btContainerTime)
        btContainerTimeMove = VBox(width='50%', height='100%', style='position: absolute; left: 0px; top: 0px')
        btContainerTime.append(btContainerTimeMove)
        btContainerTimePause = VBox(width='50%', height='100%', style='position: absolute; left: 0px; top: 0px')
        btContainerTime.append(btContainerTimePause)

        # BUTTONS:
        # Step-size drop-down
        stepsSlider = gui.Slider(3,1,7,1, style='margin: 5%; width: 90%; height: 50%')
        stepsSlider.set_on_change_listener(self.onchange_stepSize)
        stepSizeTitle = gui.Label("Step size:",style='left:0px; top:10%')

        # Speed slider
        speedSlider = gui.Slider(5,1,10,1, style='margin: 5%; width: 90%; height: 50%')
        speedSlider.set_on_change_listener(self.onchange_speedSlider)
        speedSliderTitle = gui.Label("Speed:",style='left:0px; top:10%')

        # Move drop down
        moveTime = gui.DropDown.new_from_list(('00:10','01:00','05:00', '10:00'), value='01:00', style='margin: 5%; width: 90%; height: 50%')
        moveTime.set_on_change_listener(self.onchange_moveTime)
        moveTime.set_value('01:00')
        moveTimeTitle = gui.Label("Move interval:",style='left:0px; top:10%')

        # Pause drop down
        pauseTime = gui.DropDown.new_from_list(('00:10','01:00','05:00', '10:00'),value='01:00', style='margin: 5%; width: 90%; height: 50%')
        pauseTime.set_on_change_listener(self.onchange_pauseTime)
        pauseTimeTitle = gui.Label("Pause interval:",style='left:0px; top:10%')

        # Append to containers
        btContainerStepSize.append(stepSizeTitle)
        btContainerStepSize.append(stepsSlider)
        btContainerSpeedSlider.append(speedSliderTitle)
        btContainerSpeedSlider.append(speedSlider)
        btContainerTimeMove.append(moveTimeTitle)
        btContainerTimeMove.append(moveTime)
        btContainerTimePause.append(pauseTimeTitle)
        btContainerTimePause.append(pauseTime)
        # Command buttons===============================================================================================

        # CONTAINERS:
        # Command buttons container
        btContainerCommands = VBox(width='100%', height='30%', style='position: absolute; left: 0px; top: 260px')
        btContainer.append(btContainerCommands)

        # Add-remove buttons container
        btContainerCommandsPoints = HBox(width='100%', height='50%', style='position: absolute; left: 0px; top: 0px')
        btContainerCommands.append(btContainerCommandsPoints)

        # Path generate, start stop buttons container
        btContainerCommandsPath = HBox(width='100%', height='50%', style='position: absolute; left: 0px; top: 120px')
        btContainerCommands.append(btContainerCommandsPath)

        # BUTTONS:
        # Add point button
        btAddPoint = gui.Button('Add new point', width=100, height=50)
        btAddPoint.style['margin'] = '10px'
        btAddPoint.set_on_click_listener(self.on_button_pressed_addPoint)

        # Remove point buttons
        btRemovePoint = gui.Button('Remove last point', width=100, height=50)
        btRemovePoint.style['margin'] = '10px'
        btRemovePoint.set_on_click_listener(self.on_button_pressed_removePoint)

        # Generate path button
        self.btGeneratePath = gui.Button('Generate path', width=100, height=50)
        self.btGeneratePath.style['margin'] = '10px'
        self.btGeneratePath.set_on_click_listener(self.on_button_pressed_generatePath)

        # Start/stop button
        self.btStart = gui.Button('Start', width=100, height=50)
        self.btStart.style['margin'] = '10px'
        self.btStart.set_on_click_listener(self.on_button_pressed_start)

        # Append buttons:
        btContainerCommandsPoints.append(btAddPoint)
        btContainerCommandsPoints.append(btRemovePoint)
        btContainerCommandsPath.append(self.btGeneratePath)
        btContainerCommandsPath.append(self.btStart)

        # Update widget
        self.import_points()

        return wid

    def import_points(self):
        try:
            # Read contour file
            with open('/data/contour.csv') as File:
                reader = csv.reader(File)
                rows = list(reader)
                print 'Rows:'
                print len(rows)
                if len(rows) == 4:
                    self.points_x = [int(e) for e in rows[0]]
                    self.points_y = [int(e) for e in rows[1]]
                    self.contour_x = [int(e) for e in rows[2]]
                    self.contour_y = [int(e) for e in rows[3]]
        except IOError:
            print 'No path file!'

        # Validate data
        if len(self.points_x) > 2 and len(self.points_x) == len(self.points_y):
            # Draw corner points
            try:
                self.scp.remove() # If any corner point is plotted, delete plot
            except(ValueError):
                pass
            self.scp = self.mpl.ax.scatter(self.points_x, self.points_y, c='r') # Rew-plot all corner points
            self.mpl.redraw()

            # Load path
            if len(PX)>1000 and len(PX) == len(PY):
                self.btGeneratePath.set_text('Reset') # Change text on generate path button to reset
                # Plot
                tmp_x = list(self.points_x)
                tmp_x.append(self.points_x[0])
                tmp_y = list(self.points_y)
                tmp_y.append(self.points_y[0])
                self.sc_poly = self.mpl.ax.plot(tmp_x,tmp_y,c='r') # Draw polygone
                self.mpl.redraw()
                self.btStart.set_text('Stop')

    def on_button_pressed_instr(self, widget):
        self.dialog = gui.GenericDialog(title='Instructions', width='500px')
        ContainerInstr = VBox(width=500, height=500, style='position: absolute; left: 0px; top: 0px')
        self.dialog.add_field('ContainerInstr', ContainerInstr)
        appI1 = gui.Label("1. First choose all boundary points for laser motion.\n",style='align: left; top:10px')
        appI2 = gui.Label("2. To choose a point, use movement buttons and move laser in desired position. You can manually "
                          "adjust step size form drop-down menu.\n",style='align: left; left:10px; top:10px')
        appI3 = gui.Label("3. When laser dot is in the desired position press: Add new point button. You will see a red dot appearing on the screen.\n",style='align: left; left:10px; top:10px')
        appI4 = gui.Label("4. Repeate the procedure untill all boundary points are added. If you wnat to remove last point, press: "
                             "Remove last point.\n",style='align: left; left:10px; top:10px')
        appI5 = gui.Label("5. When all ponts are added press: Generate path, which is going to determine movement region and path. "
                             "Keep in mind that the procedure can take couple of minutes. You will see yellow movement region on the screen when done."
                             "If you wnat to modify region press: Reset and repeate the procedure.\n",style='align: left; left:10px; top:10px')
        appI6 = gui.Label("6. When you want to strat laser motion press: Start. If you want to terminate motion press: Stop.\n",style='align: left; left:10px; top:10px')
        appI7 = gui.Label("7. During the motion, you can adjust laser speed by moving the Speed slider.",style='align: left; left:10px; top:10px')
        ContainerInstr.append(appI1)
        ContainerInstr.append(appI2)
        ContainerInstr.append(appI3)
        ContainerInstr.append(appI4)
        ContainerInstr.append(appI5)
        ContainerInstr.append(appI6)
        ContainerInstr.append(appI7)

        self.dialog.show(self)

    def on_button_pressed_contour(self, widget):
        global plot_data

        if START == 0:
            for i in xrange(len(self.contour_x)):
                plot_data[0] = self.contour_x[i]
                plot_data[1] = self.contour_y[i]
                time.sleep(0.005)

    def on_button_pressed_load(self, widget):
        if START == 0:
            self.import_path_app()

    def on_button_pressed_on(self, widget):
        GPIO.output(laser, 1)

    def on_button_pressed_off(self, widget):
        GPIO.output(laser, 0)

    def on_button_pressed_up(self, widget):
        """Move for step size up"""
        global plot_data
        print plot_data
        if LOCK == 0:
            if plot_data[1] + STEP < N:
                plot_data[1] += STEP
            else:
                plot_data[1] = N - 1

        print plot_data
        print START, PAUSE


    def on_button_pressed_down(self, widget):
        """Move for step size down"""
        global plot_data
        if LOCK == 0:
            if plot_data[1] - STEP >= 0:
                plot_data[1] -= STEP
            else:
                plot_data[1] = 0

    def on_button_pressed_right(self, widget):
        """Move for step size right"""
        global plot_data
        if LOCK == 0:
            if plot_data[0] + STEP < N:
                plot_data[0] += STEP
            else:
                plot_data[0] = N - 1

    def on_button_pressed_left(self, widget):
        """Move for step size left"""
        global plot_data
        if LOCK == 0:
            if plot_data[0] - STEP >= 0:
                plot_data[0] -= STEP
            else:
                plot_data[0] = 0


    def onchange_stepSize(self, emitter, new_value):
        """Set step size to new value from the drop-down menu"""
        global STEP
        i = int(new_value)
        if i == 1:
            STEP = 100
        elif i == 2:
            STEP = 500
        elif i == 3:
            STEP = 1000
        elif i == 4:
            STEP = 2000
        elif i == 5:
            STEP = 5000
        elif i == 6:
            STEP = 10000
        elif i == 7:
            STEP = 20000


    def onchange_speedSlider(self, widget, value):
        global SPEED
        SPEED = (10. - float(value))/1000.
        self.save_parameters()

    def onchange_moveTime(self, widget, value):
        global MOVE_T
        if value == '00:10':
            MOVE_T = 10
        elif value == '01:00':
            MOVE_T = 60
        elif value == '05:00':
            MOVE_T = 300
        elif value == '10:00':
            MOVE_T = 600

        self.save_parameters()

    def onchange_pauseTime(self, widget, value):
        global PAUSE_T
        if value == '00:10':
            PAUSE_T = 10
        elif value == '01:00':
            PAUSE_T = 60
        elif value == '05:00':
            PAUSE_T = 300
        elif value == '10:00':
            PAUSE_T = 600

        self.save_parameters()


    def on_button_pressed_addPoint(self, widget):
        """Add new corner point"""
        if LOCK == 0:
            # Add new corner point
            self.points_x.append(plot_data[0])
            self.points_y.append(plot_data[1])

            try:
                self.scp.remove() # If any corner point is plotted, delete plot
            except(ValueError):
                pass

            self.scp = self.mpl.ax.scatter(self.points_x, self.points_y, c='r') # Rew-plot all corner points
            self.mpl.redraw()

    def on_button_pressed_removePoint(self, widget):
        """Remove last corner point"""
        if LOCK == 0:
            # Remove last corner point
            try:
                self.points_x.pop()
            except(IndexError):
                pass
            try:
                self.points_y.pop()
            except(IndexError):
                pass
            self.scp.remove() # Remove corners plot
            self.scp = self.mpl.ax.scatter(self.points_x, self.points_y, c='r') # Re-draw corners
            self.mpl.redraw()

    def on_button_pressed_generatePath(self, widget):
        """Determine movement area and store movement path or reset all data."""
        global LOCK
        global PX, PY
        global START, PAUSE
        # Generate path:
        if LOCK == 0:
            # Check if there are at least 3 corner points added
            if len(self.points_x) > 2:
                LOCK = 1 # Lock movement
                self.btGeneratePath.set_text('Reset') # Change text on generate path button to reset
                PX, PY, self.contour_x, self.contour_y = rp.generate_polygone(self.points_x, self.points_y) # Generate movement
                self.save_parameters() # Save parameters
                # Plot
                t = time.time()
                tmp_x = list(self.points_x)
                tmp_x.append(self.points_x[0])
                tmp_y = list(self.points_y)
                tmp_y.append(self.points_y[0])
                self.sc_poly = self.mpl.ax.plot(tmp_x,tmp_y,c='r') # Draw polygone
                print 'Redraw'
                print time.time() - t
                t = time.time()
                self.mpl.redraw()
                print 'Plot updated'
                print time.time() - t
        # Reset:
        else:
            LOCK = 0
            self.btGeneratePath.set_text('Generate path') # Change button name to generate path
            self.scp.remove() # Remove corner plot
            self.points_x = [] # Reset corner points
            self.points_y = []
            self.mpl.ax.lines = []
            PAUSE = 0
            if START == 1:
                START = 0
                self.btStart.set_text('Start')

            self.mpl.redraw()

    def on_button_pressed_start(self, widget):
        """Start/Stop laser motion"""
        global START
        global PAUSE
        global startT
        if START == 0:
            if LOCK == 1:
                startT = time.time() # Mark start of motion
                PAUSE = 0 # Reset pause
                self.btStart.set_text('Stop')
                START = 1
        else:
            START = 0
            PAUSE = 0
            self.btStart.set_text('Start')

    # Load data from previous session
    def import_path_app(self):
        # Define global parameters
        global SPEED
        global START
        global PAUSE
        global LOCK
        global startT
        global MOVE_T
        global PAUSE_T
        global PX, PY

        try:
            # Read path file
            with open('/data/path.csv') as File:
                reader = csv.reader(File)
                rows = list(reader)
                PX = [int(e) for e in rows[0]]
                PY = [int(e) for e in rows[1]]
        except IOError:
            print 'No path file!'

        try:
            # Read contour file
            with open('/data/parm.csv') as File:
                reader = csv.reader(File)
                rows = list(reader)
                print 'Rows:'
                print len(rows)
                if len(rows) == 1:
                    [SPEED, MOVE_T, PAUSE_T] = [e for e in rows[0]]
                    SPEED = float(SPEED)
                    MOVE_T = int(MOVE_T)
                    PAUSE_T = int(PAUSE_T)
                    print SPEED, MOVE_T, PAUSE_T
        except IOError:
            print 'No parm file!'

        # Import contour
        self.import_points()

        # Validate data
        if len(PX)>1000 and len(PX) == len(PY):
            LOCK = 1 # Lock movement
            startT = time.time() # Mark start of motion
            PAUSE = 0 # Reset pause
            START = 1


    def save_parameters(self):
        with open('/data/parm.csv', 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([SPEED, MOVE_T, PAUSE_T])

# Load data from previous session
def import_path():
    # Define global parameters
    global SPEED
    global START
    global PAUSE
    global LOCK
    global startT
    global MOVE_T
    global PAUSE_T

    px = []
    py = []
    try:
        # Read path file
        with open('/data/path.csv') as File:
            reader = csv.reader(File)
            rows = list(reader)
            px = [int(e) for e in rows[0]]
            py = [int(e) for e in rows[1]]
    except IOError:
        print 'No path file!'

    try:
        # Read contour file
        with open('/data/parm.csv') as File:
            reader = csv.reader(File)
            rows = list(reader)
            print 'Rows:'
            print len(rows)
            if len(rows) == 1:
                [SPEED, MOVE_T, PAUSE_T] = [e for e in rows[0]]
                SPEED = float(SPEED)
                MOVE_T = int(MOVE_T)
                PAUSE_T = int(PAUSE_T)
                print SPEED, MOVE_T, PAUSE_T
    except IOError:
        print 'No parm file!'

    # Validate data
    if len(px)>1000 and len(px) == len(py):
        LOCK = 1 # Lock movement
        startT = time.time() # Mark start of motion
        PAUSE = 0 # Reset pause
        START = 1

    return px, py


def move_laser():
    global PAUSE
    global startT
    global plot_data
    count = 0

    print 'Starting laser thread...'
    print threading.currentThread().getName()
    # Setup laser=======================================================================================================
    GPIO.setmode(GPIO.BOARD) # use the Broadcom pin numbering
    GPIO.setwarnings(False) # disable warnings
    GPIO.setup(laser, GPIO.OUT)

    try:
        #setup DAC this way
        GPIO.output(laser, 1)
        print laser
        dac_x = AD5721(spibus=0,spidevice=0)
        dac_x.writeRegister(dac_x.CMD_SW_FULL_RESET,0xffff)
        dac_x.write_ctrl_reg()
        dac_x.read_ctrl_reg()
        dac_x.write_voltage(plot_data[0],plot_data[1])
    except KeyboardInterrupt:   # Press CTRL C to exit program
        dac.setVoltage(0, 0)
        dac.shutdown(0)
        GPIO.cleanup()
        sys.exit(0)

    print 'Starting thread, laser turned on...'
    time.sleep(1)

    while True:
        if START == 1:
            x = PX[count]
            y = PY[count]
            count += 1
            count %= len(PX)
        else:
            count = 0
            x = plot_data[0]
            y = plot_data[1]

        # check for pause
        if PAUSE == 0:
            # check if movement time has passed
            if time.time()-startT > MOVE_T and START == 1:
                PAUSE = 1
                startT = time.time()
                GPIO.output(laser, 0)

            try:
                #write voltage 0-65535, for X and Y
                dac_x.write_voltage(x,y)
                time.sleep(SPEED)
            except KeyboardInterrupt:   # Press CTRL C to exit program
                GPIO.output(laser, 0)
                dac.setVoltage(0, 0)
                dac.shutdown(0)
                GPIO.cleanup()
                sys.exit(0)
        elif START == 1:
            if time.time()-startT > PAUSE_T:
                PAUSE = 0
                startT = time.time()
                GPIO.output(laser, 1)




if __name__ == "__main__":

    # Load path and start laser thread==================================================================================
    PX, PY = import_path() # Load data and start thread
    LaserThread = Thread(target=move_laser) # set up plotting thread
    LaserThread.start()

    start(MyApp,
          debug=True,
          address='127.0.0.1',
          port=80,
          multiple_instance=False,
          enable_file_cache=True,
          update_interval=0.1,
          start_browser=True)
