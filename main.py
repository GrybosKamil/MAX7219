#!/usr/bin/python
# -*- coding:utf-8 -*-
from ctypes import *
import sys
import time
import binascii
from threading import Timer
import RPi.GPIO as GPIO

import argparse

from characters import CHARACTERS

hspi = CDLL('./dev_hardware_SPI.so')
hspi.DEV_HARDWARE_SPI_begin("/dev/spidev0.0")
hspi.DEV_HARDWARE_SPI_ChipSelect(3)

def convertCharacters(inputDict, order):
    outputDict = {}
    for key, value in inputDict.items():
        outputDict[key] = convertCharacter(value, order)
    return CharactersDictionary(order, outputDict)

def convertTranspose(character):
    temp = ["", "", "", "", "", "", "", ""]
    for x in range(0, 8):
        for y in range(0, 8):
            temp[y] = temp[y] + character[x][y]
    return temp

def convertCharacter(character, order):
    if order == 0:
        result = [int(x[::-1], 2) for x in character]
    elif order == 1:
        result = [int(x, 2) for x in character]
    elif order == 2:
        result = [int(x, 2) for x in convertTranspose(character)]
    elif order == 3:
        result = [int(x[::-1], 2) for x in convertTranspose(character)]
    return result

class CharactersDictionary:
    def __init__(self, order, dictionary):
        self.order = order
        self.dictionary = dictionary
    
    def getOrder(self):
        return self.order
    
    def getDictionary(self):
        return self.dictionary
    
    def getValue(self, value):
        return self.dictionary.get(value)

class CharactersDictionaryWrapper:
    def __init__(self):
        self.dicts = {}
        self.currentOrder = None

    def setDict(self, order, dictionary):
        self.dicts[order] = dictionary
    
    def setCurrentOrder(self, order):
        dictionary = self.dicts[order]
        if dictionary is None:
            raise ValueError("Dict not yet provided for order='" + order + "'")
        self.currentOrder = order

    def getCurrentOrder(self):
        return self.currentOrder

    def get(self, value):
        return self.getCurrentDict().getValue(value)

    def getCurrentDict(self):
        return self.dicts[self.currentOrder]

class MAX7219:
    def __init__(self, order):
        self.cs_pin = 8
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.cs_pin, GPIO.OUT)
        self.init(order)

    def init(self, order):
        self.order = order

        self.charactersDictionaryWrapper = CharactersDictionaryWrapper()
        self.charactersDictionaryWrapper.setDict(0, convertCharacters(CHARACTERS, 0))
        self.charactersDictionaryWrapper.setDict(1, convertCharacters(CHARACTERS, 1))
        self.charactersDictionaryWrapper.setDict(2, convertCharacters(CHARACTERS, 2))
        self.charactersDictionaryWrapper.setDict(3, convertCharacters(CHARACTERS, 3))
        self.charactersDictionaryWrapper.setCurrentOrder(self.order)

        self.writeInit(0x09,0x00,0x09,0x00)
        self.writeInit(0x0a,0x03,0x0a,0x03)
        self.writeInit(0x0b,0x07,0x0b,0x07)
        self.writeInit(0x0c,0x01,0x0c,0x01)
        self.writeInit(0x0f,0x00,0x0f,0x00)

        self.clear()
        self.refresh()

    def setValue0(self, value):
        self.value0 = value

    def setValue1(self, value):
        self.value1 = value

    def setOrder(self, order):
        self.order = order
        self.charactersDictionaryWrapper.setCurrentOrder(self.order)
        self.show()

    def getCharacter(self, value):
        return self.charactersDictionaryWrapper.get(value)

    def writeInit(self, addr0, val0, addr1, val1):
        GPIO.output(self.cs_pin, 0)
        self.writeByte(addr0)
        self.writeByte(val0)
        self.writeByte(addr1)
        self.writeByte(val1)
        GPIO.output(self.cs_pin, 1)

    def writeByte(self, Reg):
        GPIO.output(self.cs_pin, 0)
        hspi.DEV_SPI_WriteByte(Reg)

    def clear(self):
        self.preValue0 = []
        self.preValue1 = []
        self.setValue0("empty")
        self.setValue1("empty")

    def write(self, v0, v1):
        self.setValue0(v0)
        self.setValue1(v1)

    def isPendingChanges(self):
        return self.value0 != self.preValue0 or self.value1 != self.preValue1

    def refreshIfValueChanged(self):
        if not self.isPendingChanges():
            self.show()

    def refresh(self):
        self.show()
        # self.refreshIfValueChanged()
    
    def show(self):
        if self.order == 0:
            self.showOrder0()
        elif self.order == 1:
            self.showOrder1()
        elif self.order == 2:
            self.showOrder2()
        elif self.order == 3:
            self.showOrder3()
        
    def showOrder0(self):
        for i in range(0, 8):
            GPIO.output(self.cs_pin, 0)
            self.writeByte(i+1)
            self.writeByte(self.getCharacter(self.value0)[8-i-1])
            self.writeByte(i+1)
            self.writeByte(self.getCharacter(self.value1)[8-i-1])
            GPIO.output(self.cs_pin, 1)

    def showOrder1(self):
        for i in range(0, 8):
            GPIO.output(self.cs_pin, 0)
            self.writeByte(i+1)
            self.writeByte(self.getCharacter(self.value1)[i])
            self.writeByte(i+1)
            self.writeByte(self.getCharacter(self.value0)[i])
            GPIO.output(self.cs_pin, 1)
        
    def showOrder2(self):
        for i in range(0, 8):
            GPIO.output(self.cs_pin, 0)
            self.writeByte(i+1)
            self.writeByte(self.getCharacter(self.value1)[8-i-1])
            self.writeByte(i+1)
            self.writeByte(self.getCharacter(self.value0)[8-i-1])
            GPIO.output(self.cs_pin, 1)

    def showOrder3(self):
        for i in range(0, 8):
            GPIO.output(self.cs_pin, 0)
            self.writeByte(i+1)
            self.writeByte(self.getCharacter(self.value0)[i])
            self.writeByte(i+1)
            self.writeByte(self.getCharacter(self.value1)[i])
            GPIO.output(self.cs_pin, 1)

def main(order, values):
    led = MAX7219(0)

    led.write(values[0], values[1])
    led.refresh()
    led.setOrder(order)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--order', type=int, default=0, help="Define '-order' int value 0/1/2/3", choices=[0,1,2,3])
    parser.add_argument('-v', '--values', nargs=2, default=['1','2'], metavar=('fVal, sVal'), help="Provide 2 characters to display")
    args = parser.parse_args()

    order = args.order
    values = args.values
    main(order, values)