#!/usr/bin/python

# simple.py

import serial
import wx

app = wx.App()

frame = wx.Frame(None, -1, 'simple.py')
devices = wx.ListBox(frame)
devices

frame.Show()

app.MainLoop()
