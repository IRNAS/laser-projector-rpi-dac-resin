#!/usr/bin/python

import time

"""
Python Library for AD5721, AD5721R, AD5761, AD5761R, Voltage Output Digital to Analog Converter DAC using Raspberry Pi
Currently only supports Hardware SPI
Requires: RPi.GPIO & spidev libraries

Wiring:

AD5721    =======>   Raspberry Pi

CS         ------->   GPIO08 Physical Pin 24 (SPI0 CE0) => Can be changed
SDI        ------->   GPIO10 Physical Pin 19 (SPI0 MOSI) => cannot be changed in hardware SPI MODE
SCK        ------->   GPIO11 Physical Pin 23 (SPI0 SCLK) => cannot be changed in hardware SPI MODE

"""

import RPi.GPIO as GPIO
import spidev


class AD5721(object):
    """ Class for the AD5721 digital to analog converter
    """
    spi = spidev.SpiDev()
    CMD_NOP = 0x0
    CMD_WR_TO_INPUT_REG = 0x1
    CMD_UPDATE_DAC_REG = 0x2
    CMD_WR_UPDATE_DAC_REG = 0x3
    CMD_WR_CTRL_REG = 0x4
    CMD_NOP_ALT_1 = 0x5
    CMD_NOP_ALT_2 = 0x6
    CMD_SW_DATA_RESET = 0x7
    CMD_RESERVED = 0x8
    CMD_DIS_DAISY_CHAIN = 0x9
    CMD_RD_INPUT_REG = 0xA
    CMD_RD_DAC_REG = 0xB
    CMD_RD_CTRL_REG = 0xC
    CMD_NOP_ALT_3 = 0xD
    CMD_NOP_ALT_4 = 0xE
    CMD_SW_FULL_RESET = 0xF
       
    rd_ctrl_reg_cv = {
    '00' : "zero",
    '01' : "midscale",
    '10' : "full scale",
    '11' : "full scale"
    }
    
    rd_ctrl_reg_ovr = {
    '0' : "overrange disabled",
    '1' : "overrange enabled"
    }
    
    rd_ctrl_reg_b2c = {
    '0' : "bipolar straight",
    '1' : "bipolar 2s complement"
    }
    
    rd_ctrl_reg_ets = {
    '0' : "thermal shutdown off",
    '1' : "thermal shutdown on"
    }
    
    rd_ctrl_reg_iro = {
    '0' : "iro off" ,
    '1' : "iro on"
    }
    
    rd_ctrl_reg_pv = {
    '00' : "zero" ,
    '01' : "midscale",
    '10' : "full scale",
    '11' : "full scale"
    }
    
    rd_ctrl_reg_ra = {
    '000' : "-10 to +10",
    '001' : "0 to +10",
    '010' : "-5 to +5",
    '011' : "0 to +5",
    '100' : "-2.5 to +7.5",
    '101' : "-3 to +3",
    '110' : "0 to +16",
    '111' : "0 to +20"
    }

    def __init__(self,
                 spibus=None,
                 spidevice=None
                 ):
        """ Initialize AD5721 device with hardware SPI
            Chipselect default value is BCM Pin 8 (Physical Pin: 24)
            Select the bus and device number. Default values are:
            Bus = 0 ; Device = 1
            If you're not sure, just leave it default
        """
 
        if spibus is None:
            self.spibus = 0
        else:
            self.spibus = spibus

        if spidevice is None:
            self.spidevice = 0
        else:
            self.spidevice = spidevice

        # As soon as AD5721 object is created spidev bus and device are opened
        # otherwise causes memory leak and creates Errno 24
        self.spi.open(self.spibus, self.spidevice)
        self.spi.max_speed_hz = 5000000 # 5MHz
        self.spi.mode = 0b01        

    def write_ctrl_reg(self):
        data = 0b0000001001101000 # mid-scale clear, no overrange, straight, thermal on, internal ref, midscale +-10V
        #data = 0b0000001001101011 # mid-scale clear, no overrange, straight, thermal on, internal ref, midscale 0-5V         
        return self.writeRegister(self.CMD_WR_CTRL_REG,data)
        
    def write_voltage(self,voltage1,voltage2):
   
        output = int(voltage1) & 0xffff
        buf0 = (output >> 8) & 0xff
        buf1 = output & 0xff
        
        output2 = int(voltage2) & 0xffff
        buf3 = (output2 >> 8) & 0xff
        buf4 = output2 & 0xff
        
        data = self.spi.xfer2([self.CMD_WR_UPDATE_DAC_REG, buf0, buf1,self.CMD_WR_UPDATE_DAC_REG, buf3, buf4])
        return data
    
    def read_ctrl_reg(self):
        data =  self.readRegister(self.CMD_RD_CTRL_REG)
        binary_string = '{0:08b}'.format(data[0]) + '{0:08b}'.format(data[1]) + '{0:08b}'.format(data[2])
        
        print("Control register data:")
        _stat = str(binary_string[4]) + str(binary_string[5]) + str(binary_string[6]) + str(binary_string[7])
        print(' REG: ' + str(_stat))
        _stat = str(binary_string[21]) + str(binary_string[22]) + str(binary_string[23])
        print(' RA : ' + str(self.rd_ctrl_reg_ra[_stat])) 
        _stat = str(binary_string[19]) + str(binary_string[20])
        print(' PV : ' + str(self.rd_ctrl_reg_pv[_stat]))
        _stat = str(binary_string[18])
        print(' IRO: ' + str(self.rd_ctrl_reg_iro[_stat]))
        _stat = str(binary_string[17])
        print(' ETS: ' + str(self.rd_ctrl_reg_ets[_stat]))
        _stat = str(binary_string[16])
        print(' B2C: ' + str(self.rd_ctrl_reg_b2c[_stat]))
        _stat = str(binary_string[15])
        print(' OVR: ' + str(self.rd_ctrl_reg_ovr[_stat]))
        _stat = str(binary_string[13]) + str(binary_string[14])
        print(' CV : ' + str(self.rd_ctrl_reg_cv[_stat]))
        
        binary_string = '{0:08b}'.format(data[3]) + '{0:08b}'.format(data[4]) + '{0:08b}'.format(data[5])
        
        print("Control register data:")
        _stat = str(binary_string[4]) + str(binary_string[5]) + str(binary_string[6]) + str(binary_string[7])
        print(' REG: ' + str(_stat))
        _stat = str(binary_string[21]) + str(binary_string[22]) + str(binary_string[23])
        print(' RA : ' + str(self.rd_ctrl_reg_ra[_stat])) 
        _stat = str(binary_string[19]) + str(binary_string[20])
        print(' PV : ' + str(self.rd_ctrl_reg_pv[_stat]))
        _stat = str(binary_string[18])
        print(' IRO: ' + str(self.rd_ctrl_reg_iro[_stat]))
        _stat = str(binary_string[17])
        print(' ETS: ' + str(self.rd_ctrl_reg_ets[_stat]))
        _stat = str(binary_string[16])
        print(' B2C: ' + str(self.rd_ctrl_reg_b2c[_stat]))
        _stat = str(binary_string[15])
        print(' OVR: ' + str(self.rd_ctrl_reg_ovr[_stat]))
        _stat = str(binary_string[13]) + str(binary_string[14])
        print(' CV : ' + str(self.rd_ctrl_reg_cv[_stat]))

        return binary_string
    
    
    def readRegister(self, register):
        #GPIO.output(self.cs, 0)
        data =  self.spi.xfer2([register,0xFF,0xFF,register,0xFF,0xFF])
        #GPIO.output(self.cs, 1)
        
        time.sleep(0.01)
        
        #GPIO.output(self.cs, 0)
        data =  self.spi.xfer2([0x00,0xFF,0xFF,0x00,0xFF,0xFF])
        #GPIO.output(self.cs, 1)
        print "data:" + str(data)
        return data
        
    def writeRegister(self, register, value):
    
        output = int(value) & 0xffff
        buf0 = (output >> 8) & 0xff
        buf1 = output & 0xff
        data = self.spi.xfer2([register, buf0, buf1,register, buf0, buf1])
        return data

    def close(self):
        """
        Closes the device
        """
        self.spi.close
        return

    def open(self):
        """
        Manually Open the device
        """
        self.spi.open(self.spibus, self.spidevice)
        return
 