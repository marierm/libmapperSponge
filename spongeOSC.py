#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx
from wx.lib.pubsub import Publisher
import serial
from serial.tools import list_ports
import slip.SerialComm as SerialComm
import slip.ProtoSLIP as ProtoSLIP
import liblo
import threading
import math

serialPorts = list_ports.comports()
baudRates = [115200, 57600, 19200]
port = 57120                    # SuperCollider port


class SpongeView(wx.Frame):
    def __init__(self, parent, title):
        super(SpongeView, self).__init__(parent, title=title, size=(600,200))
        
        self.InitUI()
        self.Centre()
        self.Show() 

    def InitUI(self):
        panel = wx.Panel(self)
        panel.SetBackgroundColour("#DDDDDD")

        # main box
        vbox0 = wx.BoxSizer(wx.VERTICAL)
        # la premiere ligne de widgets
        hbox0 = wx.BoxSizer(wx.HORIZONTAL)

        # grid avec les textes et popups
        flexbox = wx.FlexGridSizer(2,2,2,2)
        flexbox.AddGrowableCol(1)
       
        ports = []
        for i in serialPorts:
            ports.append(i[0])
        textPort = wx.StaticText(panel, id=-1, label="Serial Port: ")
        self.choicePort = wx.Choice(panel, id=-1, choices=ports)

        rates = [];
        for i in range(0,len(baudRates)):
            rates.append(str(baudRates[i]))
        textBaud = wx.StaticText(panel, id=-1, label="Baudrate: ")
        self.choiceBaud = wx.Choice(panel, id=-1, choices=rates)
        textPath = wx.StaticText(panel, id=-1, label="OSC Path: ")
        self.oscPath = wx.TextCtrl(panel, id=-1, value="/sponge")
        textOscPort = wx.StaticText(panel, id=-1, label="OSC Port: ")
        self.oscPort = wx.TextCtrl(panel, id=-1, value="57120")


        flexbox.AddMany([
                (textPort, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL, 0),
                (self.choicePort, 1, wx.EXPAND, 0),
                (textBaud, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL, 0),
                (self.choiceBaud, 1, wx.EXPAND, 0),
                (textPath, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL, 0),
                (self.oscPath, 1, wx.EXPAND, 0),
                (textOscPort, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL, 0),
                (self.oscPort, 1, wx.EXPAND, 0)
        ])

        hbox0.Add(flexbox, 1, flag=wx.EXPAND|wx.ALL, border=2)


        self.openButton = wx.ToggleButton(panel, label='Open Port')
        hbox0.Add(self.openButton, 1, flag=wx.EXPAND|wx.ALL, border=2)

        vbox0.Add(hbox0, 0, flag=wx.EXPAND|wx.ALL, border=2)
        # tu rajoutes dans vbox0 pour aller en dessous...
        self.checkList = wx.CheckListBox(panel)
        
        vbox0.Add(self.checkList, 1, wx.EXPAND, border=5)
        panel.SetSizer(vbox0)

class SpongeController:
    def __init__(self, app):
        self.sponge = Sponge()  # Model
        self.view = SpongeView(None, 'Sponge') # View
        self.view.openButton.Bind(wx.EVT_TOGGLEBUTTON, self.openSpongePort)
        self.view.checkList.Bind(wx.EVT_CHECKLISTBOX, self.sensorActivation)

        sensorList = self.sponge.sensorNames
        for i in range(0,self.sponge.numButt):
            sensorList.append("button" + str(i))
        self.view.checkList.Set(sensorList)
        Publisher().subscribe(self.sensorActivationChanged, "sensorActivation")

    def openSpongePort(self, evt):
        if (evt.GetInt() == 1):
            self.sponge.openPort(
                port=self.view.choicePort.GetStringSelection(),
                baudrate=self.view.choiceBaud.GetStringSelection())
        else:
            self.sponge.go = 0

    def sensorActivation(self, evt):
        index = evt.GetSelection()
        name = self.view.checkList.GetString(index)
        if self.view.checkList.IsChecked(index):
            self.sponge.activateFeature(name)
            print name, "activated."
        else:
            self.sponge.deactivateFeature(name)
            print name, "deactivated."

    def sensorActivationChanged(self, msg):
        index = self.view.checkList.Items.index(msg.data[0])
        check = msg.data[1]
        self.view.checkList.Check(index, check)

class Sponge():
    def __init__(self):
        # self.dev = mapper.device("sponge", 9000)
        self.go = 1

        self.sensorNames = [
            'acc1x', 'acc1y', 'acc1z',
            'acc2x', 'acc2y', 'acc2z',
            'fsr1', 'fsr2']
        self.numButt = 10
        self.numCont = len(self.sensorNames)
        self.packetSize = (self.numCont * 2) + (self.numButt % 8)

    def readAndUpdate(self):
        while (self.go):
            self.dev.poll(1)
            # Make sure we have a complete packet before going on.
            self.bytes = ProtoSLIP.decodeFromSLIP(self.ser)
            while (len(self.bytes) != self.packetSize):
                self.bytes = ProtoSLIP.decodeFromSLIP(self.ser)
            # for i in self.activeFeatures:
            #     i.update()
            self.sendOSC(self.bytes);
        SerialComm.disconnectFromSerialPort(self.ser)
        print "Port closed."
        return

    def sendOSC():
        liblo.send(target, self.bytes)

    

    def openPort(self, port='/dev/ttyUSB0', baudrate=115200):
        self.ser = SerialComm.connectToSerialPort(port, baudrate)
        self.thread = threading.Thread(target=self.readAndUpdate)
        self.thread.daemon = True
        self.thread.start()

if __name__ == '__main__':
    app = wx.App()
    SpongeController(app)
    app.MainLoop()
