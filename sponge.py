#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx
from wx.lib.pubsub import Publisher
import serial
from serial.tools import list_ports
import slip.SerialComm as SerialComm
import slip.ProtoSLIP as ProtoSLIP
import mapper
import threading
import math

serialPorts = list_ports.comports()
baudRates = [115200, 57600, 19200]

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

        flexbox.AddMany([
                (textPort, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL, 0),
                (self.choicePort, 1, wx.EXPAND, 0),
                (textBaud, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL, 0),
                (self.choiceBaud, 1, wx.EXPAND, 0)])

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
        self.view.checkList.Bind(wx.EVT_CHECKLISTBOX, self.featureActivation)

        featureList = []
        for i in self.sponge.features:
            featureList.append(i.name)
        self.view.checkList.Set(featureList)
        Publisher().subscribe(self.featureActivationChanged, "featureActivation")

        for i in self.sponge.features:
            i.activate()

    def featureActivationChanged(self, msg):
        index = self.view.checkList.Items.index(msg.data[0])
        check = msg.data[1]
        self.view.checkList.Check(index, check)

    def openSpongePort(self, evt):
        if (evt.GetInt() == 1):
            self.sponge.openPort(
                port=self.view.choicePort.GetStringSelection(),
                baudrate=self.view.choiceBaud.GetStringSelection())
        else:
            self.sponge.go = 0

    def featureActivation(self, evt):
        index = evt.GetSelection()
        name = self.view.checkList.GetString(index)
        if self.view.checkList.IsChecked(index):
            self.sponge.activateFeature(name)
            print name, "activated."
        else:
            self.sponge.deactivateFeature(name)
            print name, "deactivated."

class Sponge():
    def __init__(self):
        self.dev = mapper.device("sponge", 9000)
        self.go = 1

        self.sensorNames = [
            'acc1x', 'acc1y', 'acc1z',
            'acc2x', 'acc2y', 'acc2z',
            'fsr1', 'fsr2']
        self.numButt = 10
        self.numCont = len(self.sensorNames)
        self.packetSize = (self.numCont * 2) + (self.numButt % 8)

        self.initFeatures()


    def readAndUpdate(self):
        while (self.go):
            self.dev.poll(1)
            # Make sure we have a complete packet before going on.
            self.bytes = ProtoSLIP.decodeFromSLIP(self.ser)
            while (len(self.bytes) != self.packetSize):
                self.bytes = ProtoSLIP.decodeFromSLIP(self.ser)
            for i in self.activeFeatures:
                i.update()
        SerialComm.disconnectFromSerialPort(self.ser)
        print "Port closed."
        return

    def getFeature(self, name):
        for i in self.features:
            if (i.name == name):
                return i
        print "Error: No feature named", name

    def openPort(self, port='/dev/ttyUSB0', baudrate=115200):
        self.ser = SerialComm.connectToSerialPort(port, baudrate)
        self.thread = threading.Thread(target=self.readAndUpdate)
        self.thread.daemon = True
        self.thread.start()

    def activateFeature(self, featureName):
        feature = self.getFeature(featureName)
        feature.activate()

    def deactivateFeature(self, featureName):
        feature = self.getFeature(featureName)
        feature.deactivate()

    def initFeatures(self):
        self.features = []
        self.activeFeatures = []
        for i, sensorName in enumerate(self.sensorNames):
            self.features.append(Feature(
                sponge = self,
                function = self.createContFunc(i),
                # function = lambda sponge, i=i: (sponge.bytes[i*2]<<8) + sponge.bytes[(i*2)+1],
                inputs = (),
                name = sensorName,
                dType = 'i',
                unit = '',
                mn = 0,
                mx = 1023))
        for i  in range(self.numButt):
            self.features.append(Feature(
                sponge = self,
                function = self.createButtonFunc(i),
                inputs = (),
                name = 'button' + str(i),
                dType = 'i',
                unit = '',
                mn = 0,
                mx = 1))
        self.features.append(Feature(
            sponge = self,
            function = self.createAtanFunc(),
            inputs = ( self.getFeature('acc1x'), self.getFeature('acc1z') ),
            name = 'roll1',
            dType = 'f',
            unit = '',
            mn = -math.pi,
            mx = math.pi))

    def createContFunc(self, i):
        def func(sponge):
            val = (sponge.bytes[i*2]<<8) + sponge.bytes[(i*2)+1]
            return val
        return func

    def createButtonFunc(self, buttNum):
        def func(sponge):
            val = (
                (sponge.bytes[sponge.numCont*2]<<8) + sponge.bytes[(sponge.numCont*2)+1]
                ) >> buttNum & 1
            return val
        return func

    def createAtanFunc(self):
        def func(sponge, *inputs):
            val = math.atan2(inputs[0].value - 512, inputs[1].value - 512)
            return val
        return func

class Feature():
    def __init__(self, sponge, function, inputs,
                 name='Feature', dType='f', unit='', mn=0.0, mx=1.0):
        self.sponge = sponge
        self.dev = sponge.dev
        self.name = name
        self.dType = dType
        self.unit = unit
        self.mn = mn
        self.mx = mx
        self.inputs = inputs
        self.function = function
        self.isActive = False
        self.children = []
    def update(self):
        self.value = self.function(self.sponge, *self.inputs)
        self.mapperOutput.update(self.value)
    def activate(self):
        if (not self.isActive):
            for i in self.inputs:
                i.activate
                i.children.append(self)
            self.sponge.activeFeatures.append(self)
            self.mapperOutput = self.dev.add_output(self.name, 1, self.dType, self.unit, self.mn, self.mx)
            self.isActive = True
            Publisher().sendMessage("featureActivation", (self.name, True))

    def deactivate(self):
        if (self.isActive):
            for i in self.children:
                i.deactivate
                self.children.remove(i)
            self.sponge.activeFeatures.remove(self)
            self.dev.remove_output(self.mapperOutput)
            self.isActive = False
            Publisher().sendMessage(("featureActivation"), (self.name, False))


if __name__ == '__main__':
    app = wx.App()
    SpongeController(app)
    app.MainLoop()
