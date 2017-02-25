""" 
A simple demonstration of a serial port monitor that plots live
data using PyQwt.

The monitor expects to receive single-byte data packets on the 
serial port. Each received byte is understood as a biofeedback
reading and is shown on a live chart.

Eli Bendersky (eliben@gmail.com)
License: this code is in the public domain
Last modified: 07.08.2009
"""
import random, sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import PyQt4.Qwt5 as Qwt
import Queue
from scipy import signal, fft
from numpy import arange

from com_monitor import ComMonitorThread
from eblib.serialutils import full_port_name, enumerate_serial_ports
from eblib.utils import get_all_from_queue, get_item_from_queue
from livedatafeed import LiveDataFeed


class PlottingDataMonitor(QMainWindow):
    def __init__(self, parent=None):
        super(PlottingDataMonitor, self).__init__(parent)

        self.update_freq = 50

	self.xaxis_min1  = 0
	self.xaxis_max1  = 60
	self.xaxis_step1 = 5

	self.xaxis_min2  = 0
	self.xaxis_max2  = 12
	self.xaxis_step2 = 1

        #Pulse
	self.yaxis_min_pulse  = 0
	self.yaxis_max_pulse  = 2.5
	self.yaxis_step_pulse = 0.5

        #HR
	self.yaxis_min_hr  = 0
	self.yaxis_max_hr  = 200
	self.yaxis_step_hr = 20

        #FFT
	self.yaxis_min_fft  = 0
	self.yaxis_max_fft  = 1
	self.yaxis_step_fft = 0.1
	
	self.xaxis_max_it = 1

        self.monitor_active = False
        self.com_monitor = None
        self.com_data_q = None
        self.com_error_q = None
        self.livefeed = LiveDataFeed()
        self.biofeedback_samples = []
        self.timer = QTimer()
        
        self.create_menu()
        self.create_main_frame()
        self.create_status_bar()
        
    def make_data_box(self, name):
        label = QLabel(name)
        qle = QLineEdit()
        qle.setEnabled(False)
        qle.setFrame(False)
        return (label, qle)
        
    def create_plot_pulse1(self):
        plot = Qwt.QwtPlot(self)
        plot.setCanvasBackground(Qt.black)
        plot.setAxisTitle(Qwt.QwtPlot.xBottom, 'Time')
        plot.setAxisScale(Qwt.QwtPlot.xBottom, self.xaxis_min1, self.xaxis_max1, self.xaxis_step1)
        plot.setAxisTitle(Qwt.QwtPlot.yLeft, 'Voltage')
        plot.setAxisScale(Qwt.QwtPlot.yLeft, self.yaxis_min_pulse, self.yaxis_max_pulse, self.yaxis_step_pulse)
        plot.replot()
        
        curve = Qwt.QwtPlotCurve('')
        curve.setRenderHint(Qwt.QwtPlotItem.RenderAntialiased)
        pen = QPen(QColor('limegreen'))
        pen.setWidth(2)
        curve.setPen(pen)
        curve.attach(plot)
        
        return plot, curve

    def create_plot_pulse2(self):
        plot = Qwt.QwtPlot(self)
        plot.setCanvasBackground(Qt.black)
        plot.setAxisTitle(Qwt.QwtPlot.xBottom, 'Time')
        plot.setAxisScale(Qwt.QwtPlot.xBottom, self.xaxis_min2, self.xaxis_max2, self.xaxis_step2)
        plot.setAxisTitle(Qwt.QwtPlot.yLeft, 'Voltage')
        plot.setAxisScale(Qwt.QwtPlot.yLeft, self.yaxis_min_pulse, self.yaxis_max_pulse, self.yaxis_step_pulse)
        plot.replot()
        
        curve = Qwt.QwtPlotCurve('')
        curve.setRenderHint(Qwt.QwtPlotItem.RenderAntialiased)
        pen = QPen(QColor('limegreen'))
        pen.setWidth(2)
        curve.setPen(pen)
        curve.attach(plot)
        
        return plot, curve

    def create_plot_hr1(self):
        plot = Qwt.QwtPlot(self)
        plot.setCanvasBackground(Qt.black)
        plot.setAxisTitle(Qwt.QwtPlot.xBottom, 'Time')
        plot.setAxisScale(Qwt.QwtPlot.xBottom, self.xaxis_min1, self.xaxis_max1, self.xaxis_step1)
        plot.setAxisTitle(Qwt.QwtPlot.yLeft, 'BPM')
        plot.setAxisScale(Qwt.QwtPlot.yLeft, self.yaxis_min_hr, self.yaxis_max_hr, self.yaxis_step_hr)
        plot.replot()
        
        curve = Qwt.QwtPlotCurve('')
        curve.setRenderHint(Qwt.QwtPlotItem.RenderAntialiased)
        pen = QPen(QColor('limegreen'))
        pen.setWidth(2)
        curve.setPen(pen)
        curve.attach(plot)
        
        return plot, curve

    def create_plot_hr2(self):
        plot = Qwt.QwtPlot(self)
        plot.setCanvasBackground(Qt.black)
        plot.setAxisTitle(Qwt.QwtPlot.xBottom, 'Time')
        plot.setAxisScale(Qwt.QwtPlot.xBottom, self.xaxis_min2, self.xaxis_max2, self.xaxis_step2)
        plot.setAxisTitle(Qwt.QwtPlot.yLeft, 'BPM')
        plot.setAxisScale(Qwt.QwtPlot.yLeft, self.yaxis_min_hr, self.yaxis_max_hr, self.yaxis_step_hr)
        plot.replot()
        
        curve = Qwt.QwtPlotCurve('')
        curve.setRenderHint(Qwt.QwtPlotItem.RenderAntialiased)
        pen = QPen(QColor('limegreen'))
        pen.setWidth(2)
        curve.setPen(pen)
        curve.attach(plot)
        
        return plot, curve

    def create_plot_fft1(self):
        plot = Qwt.QwtPlot(self)
        plot.setCanvasBackground(Qt.black)
        plot.setAxisTitle(Qwt.QwtPlot.xBottom, 'Time')
        plot.setAxisScale(Qwt.QwtPlot.xBottom, self.xaxis_min1, self.xaxis_max1, self.xaxis_step1)
        plot.setAxisTitle(Qwt.QwtPlot.yLeft, 'Frequency')
        plot.setAxisScale(Qwt.QwtPlot.yLeft, self.yaxis_min_fft, self.yaxis_max_fft, self.yaxis_step_fft)
        plot.replot()
        
        curve = Qwt.QwtPlotCurve('')
        curve.setRenderHint(Qwt.QwtPlotItem.RenderAntialiased)
        pen = QPen(QColor('limegreen'))
        pen.setWidth(2)
        curve.setPen(pen)
        curve.attach(plot)

        grid = Qwt.QwtPlotGrid()
        grid.attach(plot)
        
        return plot, curve

    def create_plot_fft2(self):
        plot = Qwt.QwtPlot(self)
        plot.setCanvasBackground(Qt.black)
        plot.setAxisTitle(Qwt.QwtPlot.xBottom, 'Time')
        plot.setAxisScale(Qwt.QwtPlot.xBottom, self.xaxis_min2, self.xaxis_max2, self.xaxis_step2)
        plot.setAxisTitle(Qwt.QwtPlot.yLeft, 'Frequency')
        plot.setAxisScale(Qwt.QwtPlot.yLeft, self.yaxis_min_fft, self.yaxis_max_fft, self.yaxis_step_fft)
        plot.replot()
        
        curve = Qwt.QwtPlotCurve('')
        curve.setRenderHint(Qwt.QwtPlotItem.RenderAntialiased)
        pen = QPen(QColor('limegreen'))
        pen.setWidth(2)
        curve.setPen(pen)
        curve.attach(plot)
        
        return plot, curve

    def create_status_bar(self):
        self.status_text = QLabel('Monitor idle')
        self.statusBar().addWidget(self.status_text, 1)

    def create_main_frame(self):
        # Port name
        #
        portname_l, self.portname = self.make_data_box('COM Port:')
        
        portname_layout = QHBoxLayout()
        portname_layout.addWidget(portname_l)
        portname_layout.addWidget(self.portname, 0)
        portname_layout.addStretch(1)
        portname_groupbox = QGroupBox('COM Port')
        portname_groupbox.setLayout(portname_layout)
        
        # Plot
        #
        self.plot_pulse1, self.curve_pulse1 = self.create_plot_pulse1()
        self.plot_pulse2, self.curve_pulse2 = self.create_plot_pulse2()
        self.plot_hr1, self.curve_hr1 = self.create_plot_hr1()
        self.plot_hr2, self.curve_hr2 = self.create_plot_hr2()
        self.plot_fft1, self.curve_fft1 = self.create_plot_fft1()
        self.plot_fft2, self.curve_fft2 = self.create_plot_fft2()

        plot_layout = QGridLayout()
        plot_layout.addWidget(self.plot_pulse1, 0, 0)
        plot_layout.addWidget(self.plot_pulse2, 0, 1)
        plot_layout.addWidget(self.plot_hr1, 1, 0)
        plot_layout.addWidget(self.plot_hr2, 1, 1)
        plot_layout.addWidget(self.plot_fft1, 2, 0)
        plot_layout.addWidget(self.plot_fft2, 2, 1)
        #self.timer.setInterval(1000.0 / 50)
        
        plot_groupbox = QGroupBox('Plot')
        plot_groupbox.setLayout(plot_layout)
        
        # Main frame and layout
        #
        self.main_frame = QWidget()
        main_layout = QVBoxLayout()
        main_layout.addWidget(portname_groupbox)
        main_layout.addWidget(plot_groupbox)
        main_layout.addStretch(1)
        self.main_frame.setLayout(main_layout)
        
        self.setCentralWidget(self.main_frame)
        self.set_actions_enable_state()

    def create_menu(self):
        self.file_menu = self.menuBar().addMenu("&File")
        
        selectport_action = self.create_action("Select COM &Port...",
            shortcut="Ctrl+P", slot=self.on_select_port, tip="Select a COM port")
        self.start_action = self.create_action("&Start monitor",
            shortcut="Ctrl+M", slot=self.on_start, tip="Start the data monitor")
        self.stop_action = self.create_action("&Stop monitor",
            shortcut="Ctrl+T", slot=self.on_stop, tip="Stop the data monitor")
        exit_action = self.create_action("E&xit", slot=self.close, 
            shortcut="Ctrl+X", tip="Exit the application")
        
        self.start_action.setEnabled(False)
        self.stop_action.setEnabled(False)
        
        self.add_actions(self.file_menu, 
            (   selectport_action, self.start_action, self.stop_action,
                None, exit_action))
            
        self.help_menu = self.menuBar().addMenu("&Help")
        about_action = self.create_action("&About", 
            shortcut='F1', slot=self.on_about, 
            tip='About the monitor')
        
        self.add_actions(self.help_menu, (about_action,))

    def set_actions_enable_state(self):
        if self.portname.text() == '':
            start_enable = stop_enable = False
        else:
            start_enable = not self.monitor_active
            stop_enable = self.monitor_active
        
        self.start_action.setEnabled(start_enable)
        self.stop_action.setEnabled(stop_enable)

    def on_about(self):
        msg = __doc__
        QMessageBox.about(self, "About the demo", msg.strip())
    
    def on_select_port(self):
        ports = list(enumerate_serial_ports())
        if len(ports) == 0:
            QMessageBox.critical(self, 'No ports',
                'No serial ports found')
            return
        
        item, ok = QInputDialog.getItem(self, 'Select a port',
                    'Serial port:', ports, 0, False)
        
        if ok and not item.isEmpty():
            self.portname.setText(item)            
            self.set_actions_enable_state()

    def on_stop(self):
        """ Stop the monitor
        """
        if self.com_monitor is not None:
            self.com_monitor.join(0.01)
            self.com_monitor = None

        self.monitor_active = False
        self.timer.stop()
        self.set_actions_enable_state()
        
        self.status_text.setText('Monitor idle')
    
    def on_start(self):
        """ Start the monitor: com_monitor thread and the update
            timer
        """
        if self.com_monitor is not None or self.portname.text() == '':
            return
        
        self.data_q = Queue.Queue()
        self.error_q = Queue.Queue()
        self.com_monitor = ComMonitorThread(
            self.data_q,
            self.error_q,
            full_port_name(str(self.portname.text())),
            9600)
        self.com_monitor.start()
        
        com_error = get_item_from_queue(self.error_q)
        if com_error is not None:
            QMessageBox.critical(self, 'ComMonitorThread error',
                com_error)
            self.com_monitor = None

        self.monitor_active = True
        self.set_actions_enable_state()
        
        self.timer = QTimer()
        self.connect(self.timer, SIGNAL('timeout()'), self.on_timer)

        if self.update_freq > 0:
            self.timer.start(1000.0 / self.update_freq)
        
        self.status_text.setText('Monitor running')
    
    def on_timer(self):
        """ Executed periodically when the monitor update timer
            is fired.
        """
        self.read_serial_data()
        self.update_monitor()

    def update_monitor(self):
        """ Updates the state of the monitor window with new 
            data. The livefeed is used to find out whether new
            data was received since the last update. If not, 
            nothing is updated.
        """

        if self.livefeed.has_new_data:
            data = self.livefeed.read_data()
            self.biofeedback_samples.append(
                (data['timestamp'], data['biofeedback']))

            xdata = [s[0] for s in self.biofeedback_samples]
            ydata = [s[1] for s in self.biofeedback_samples]

	    if xdata[len(xdata)-1] > self.xaxis_max2*self.xaxis_max_it:
                #Window draw
                diff = xdata[len(xdata)-1] - self.xaxis_max2
                self.plot_pulse2.setAxisScale(Qwt.QwtPlot.xBottom, self.xaxis_min2 + diff, self.xaxis_max2 + diff, 1)
                self.plot_hr2.setAxisScale(Qwt.QwtPlot.xBottom, self.xaxis_min2 + diff, self.xaxis_max2 + diff, 1)
                self.plot_fft2.setAxisScale(Qwt.QwtPlot.xBottom, self.xaxis_min2 + diff, self.xaxis_max2 + diff, 1)

	    if xdata[len(xdata)-1] > self.xaxis_max1*self.xaxis_max_it:
                #Window draw
                diff = xdata[len(xdata)-1] - self.xaxis_max
                self.plot_pulse1.setAxisScale(Qwt.QwtPlot.xBottom, self.xaxis_min1 + diff, self.xaxis_max1 + diff, 1)
                self.plot_hr1.setAxisScale(Qwt.QwtPlot.xBottom, self.xaxis_min1 + diff, self.xaxis_max1 + diff, 1)
                self.plot_fft1.setAxisScale(Qwt.QwtPlot.xBottom, self.xaxis_min1 + diff, self.xaxis_max1 + diff, 1)

                #Clear and draw
	        #self.plot.setAxisScale(Qwt.QwtPlot.xBottom, self.xaxis_max*self.xaxis_max_it, self.xaxis_max*(self.xaxis_max_it+1), 1)
                #Keep all
                #self.plot.setAxisScale(Qwt.QwtPlot.xBottom, 0, self.xaxis_max*(self.xaxis_max_it+1), 1)
	        #self.xaxis_max_it += 1

            #Pulse 1 & 2
            self.curve_pulse1.setData(xdata, ydata)
            self.plot_pulse1.replot()

            self.curve_pulse2.setData(xdata, ydata)
            self.plot_pulse2.replot()

            #HR 1 & 2
            peakind = signal.find_peaks_cwt(ydata, arange(1,50))
            for i in range(1,len(peakind)):
                print peakind[i]
                ydata_hr[i-1] = 60 / (xdata[peakind[i]] - xdata[peakind[i-1]])
                xdata_hr[i-1] = xdata[peakind[i]]

            self.curve_hr1.setData(xdata_hr,ydata_hr)
            self.plot_hr1.replot()

            self.curve_hr2.setData(xdata_hr,ydata_hr)
            self.plot_hr2.replot()
            
            #FFT 1 & 2
            ydata_fft = fft(ydata_hr)
            self.curve_fft1.setData(xdata_hr,ydata_fft)
            self.plot_fft1.replot()

            self.curve_fft2.setData(xdata_hr,ydata_fft)
            self.plot_fft2.replot()
            
            
    def read_serial_data(self):
        """ Called periodically by the update timer to read data
            from the serial port.
	"""
	qdata = list(get_all_from_queue(self.data_q))
	
        if len(qdata) > 0:
            print ("len: " + str(len(qdata)))
            for ind in range(0,len(qdata)):
                data = dict(timestamp=qdata[ind][1], biofeedback=qdata[ind][0])
                print ("xd " + str(qdata[ind][1]) + " yd " + str(qdata[ind][0]))
                self.livefeed.add_data(data)
    
    # The following two methods are utilities for simpler creation
    # and assignment of actions
    #
    def add_actions(self, target, actions):
        for action in actions:
            if action is None:
                target.addSeparator()
            else:
                target.addAction(action)

    def create_action(  self, text, slot=None, shortcut=None, 
                        icon=None, tip=None, checkable=False, 
                        signal="triggered()"):
        action = QAction(text, self)
        if icon is not None:
            action.setIcon(QIcon(":/%s.png" % icon))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tip is not None:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        if slot is not None:
            self.connect(action, SIGNAL(signal), slot)
        if checkable:
            action.setCheckable(True)
        return action


def main():
    app = QApplication(sys.argv)
    form = PlottingDataMonitor()
    form.show()
    app.exec_()


if __name__ == "__main__":
    main()
    
    

