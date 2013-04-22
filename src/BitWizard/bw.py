

"""
.. module::BitWizard.bw
   :platform: Any Unix with /dev/spidevX.X devices
"""

from spi_ctypes import *
from ctypes import *

import struct
import time
from fcntl import ioctl,fcntl
import posix
from time import sleep
import socket
import threading

# Try to import SMBus, module is NOT needed if I2C is not used
try:
    from smbus import SMBus
except:
    pass

# Constants for BitWizzard Functions

Print       = 0x00
Ident       = 0x01
Serial      = 0x02

Contrast    = 0x12
Backlight   = 0x13
InitLcd     = 0x14

class ATTiny():
    ADCChannelConfig = {0:0x07,1:0x03,3:0x2,4:0x01,6:0x00}
    AddFor1V1 = 0x80

class ATMega():
    ADCChannelConfig = {0:0x47,1:0x46}
    AddFor1V1 = 0x80
#
# NETPnp is under construction and not functional (yet)
#
class NETPnp(object):
    Port = None
    UDPSocket=None
    
    def __init__(self,Port=50000):
        self.Port=Port
        self.UDPServer = treading.Thread(target= self.ScanListener)
        self.UDPServer.start()
        
    def ScanListener(self):
        self.UDPSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.UDPSocket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.UDPSocket.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
        self.UDPSocket.bind(('',self.Port))
        while True:
            Message,Address = self.UDPSocket.recvfrom(1024)
            print Address, Message
            if Message == 'BitWizardNet':
                pass
            self.UDPSocket.sendto('BWNET',Address)

    def scan(self):
        Socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        Socket.bind(('', 0))
        Socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto("BitWizardNet",('<broadcast>',50000))
        
        m,a = s.recvfrom(1000)
        print m,a


class NET(object):
    Port = 50000
    Server=None
    Socket=None
    TCPServer = None
    
    def _NetTransaction(self,OutBuffer,read=0):
        buf='  '
        if self.Socket == None:
            self.NetInit()
        if self.Socket != None:
            bsend = self.Socket.send(struct.pack('H',read)+OutBuffer)
            if bsend == len(OutBuffer)+2:
                buf =self.Socket.recv(100)
            self.Socket.close()
            self.Socket=None
        return 0,buf
                
    def RequestHandler(self,Socket):
        OutBuffer=Socket.recv(100)
        r,b = self.Transaction(OutBuffer[2:],struct.unpack('H',OutBuffer[0:2])[0])
        Socket.send(b)

    def NetInit(self):
        self.Socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.Socket.connect((self.Server,self.Port))
        
    def ListenerTread(self):
        self.Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.Socket.bind((socket.gethostname(),self.Port))
        self.Socket.listen(5)
        while 1:
            C, A = self.Socket.accept()
            self.TCPServer = threading.Thread(target = self.RequestHandler, args=(C,))
            self.TCPServer.start()

    def __del__(self):
        if self.TCPServer != None:
            self.TCPServer = None
        if self.Socket != None:
            self.Socket.close()


class _Bus(object):

    def Read_Int8(self,Address,Register):
        return struct.unpack('b',self.Transaction(chr(Address+1)+chr(Register),3)[1][2])[0]

    def Write_Int8(self,Address,Register,Int8):
        self.Transaction(chr(Address)+chr(Register)+struct.pack('b',Int8))
    
    def Read_uInt8(self,Address,Register):
        return struct.unpack('B',self.Transaction(chr(Address+1)+chr(Register),3)[1][2])[0]

    def Write_uInt8(self,Address,Register,uInt8):
        self.Transaction(chr(Address)+chr(Register)+struct.pack('B',uInt8))

    def Read_uInt8s(self,Address,Register,Number):
        pass

    def Write_uInt8s(self,Address,Register,*Bytes):
        self.Transaction(chr(Address)+chr(Register)+''.join([chr(b) for b in Bytes])) 

    def Read_uInt16(self,Address,Register):
        return struct.unpack('H',self.Transaction(chr(Address+1)+chr(Register),6)[1][2:4])[0]

    def Write_uInt16(self,Address,Register,uInt16):
        self.Transaction(chr(Address)+chr(Register)+struct.pack('H',uInt16))

    def Read16s(self,Address,Register,Number):
        pass

    def Write16s(self,Address,Register,*Word):
        pass
                             
    def Read_Int32(self,Address,Register):
        return struct.unpack('i',self.Transaction(chr(Address+1)+chr(Register),6)[1][2:6])[0]

    def Write_Int32(self,Address,Register,Int32):
        self.Transaction(chr(Address)+chr(Register)+struct.pack('i',Int32))

    def Read_uInt32(self,Address,Register):
        return struct.unpack('I',self.Transaction(chr(Address+1)+chr(Register),6)[1][2:6])[0]

    def Write_uInt32(self,Address,Register,uInt32):
        self.Transaction(chr(Address)+chr(Register)+struct.pack('I',uIt32))

    def Read32s(self,Address,Register,Number):
        pass

    def Write32s(self,Address,Register, *Long):
        pass

    def Read_String(self,Address,Register,MaxLen=0x20):
        ret,rxbuf = self.Transaction(chr(Address+1)+chr(Register),MaxLen)
        return string_at(addressof(rxbuf)+2)    

    def Write_String(self,Address,Register,String,MaxLen=0x20):
        if len(String)>MaxLen:
           String=String[0:20]                  
        self.Transaction(chr(Address)+chr(Register)+String)
                             
        
class I2C(_Bus,NET):
    Devices = {}
    DeviceList= {}
    class Device():
        """class respresening a device connected to the bus,
        instances are created automatically"""
        def __init__(self,address,InUseBy=None,Bus = None,Ident=''):
            """address = int (0x00-0xFF), address of this device
            Ident   = The Identification of the device for scan matching, default:''
            InUseBy = If an Instance of a device-class is created, InUseBy points to that Instance"""
            self.Ident = Ident
            self.InUseBy = InUseBy
            VersionStrip =Ident.split(' ')[0].lower()
            if Ident !='' and VersionStrip in I2C.DeviceList:
                self.InUseBy = I2C.DeviceList[VersionStrip](Bus,address)
            else:
                self.Type=None
            if self.InUseBy!=None:
                self.InUseBy.Ident=VersionStrip

    def __init__(self,device=0,Port=None,Server=None):
        #  TODO: Ckeck for Raspberry Pi, and its version in /Proc/CPUInfo 
        self.Port = Port
        self.Server=Server
        if self.Server != None:  # TCP Client mode
            self.NetInit()
            self.Transaction=self._NetTransaction
        else:
            try:
                self.I2cBus = SMBus(device)
            except :
                print 'Need python-smbus for I2C bus to work'
                print ''
                print 'To install: sudo apt-get install python-smbus'
                return None
            if self.Port != None: #TCP Server Mode
                self.ServerThread = threading.Thread(target=self.ListenerTread)
                self.ServerThread.start()

    def Close(self):
        self.I2cBus.close()

    def Transaction(self, OutBuffer,read=0):
        if read!=0:
            try:
                return 0,'  '+''.join([chr(m) for m in self.I2cBus.read_i2c_block_data((ord(OutBuffer[0])>>1),ord(OutBuffer[1]))])
            except IOError:
                return 0,"  "
        else:
            self.I2cBus.write_i2c_block_data(ord(OutBuffer[0])>>1  ,ord(OutBuffer[1]), [ord(m) for m in OutBuffer[2:]])           
            return 0,None

    #
    # TODO: change Transaction to _Bus.Read_String
    #
    def scan(self,Display=None,line=0):
        for i in range(0x00,0xFF,0x02):
            ret, buf = self.Transaction(chr(i)+chr(Ident),0x20)

            Identification =""
            for c in buf[2:]:
                if ord(c)==0: break
                if ord(c) in range(32,127):
                    Identification +=c

            if Identification != "":
                if i in self.Devices:
                    self.Devices[i].Ident=Identification
                else:
                    self.Devices[i]=I2C.Device(i,Ident=Identification,Bus=self)
            if Display!=None:
                ProgressBar(i,minval=0, maxval=0xFF , Display = Display, y=line)
                sleep(.05)

    def AddDevice(self,Address, InUseBy):
        self.Devices[Address]=I2C.Device(Address,InUseBy=InUseBy,Bus=self)




class SPI(_Bus,NET):
    """class respresenting an SPI Bus"""
    ReadSpeed = 50000
    WriteSpeed = 100000
    Devices = {}
    DeviceList={}
    class Device():
        """class respresening a device connected to the bus,
        instances are created automatically"""
        def __init__(self,address,InUseBy=None,Bus = None,Ident=''):
            """address = int (0x00-0xFF), address of this device
            Ident   = The Identification of the device for scan matching, default:''
            InUseBy = If an Instance of a device-class is created, InUseBy points to that Instance"""
            self.Ident = Ident
            self.InUseBy = InUseBy
            VersionStrip =Ident.split(' ')[0].lower()
            if Ident !='' and VersionStrip in SPI.DeviceList:
                self.InUseBy = SPI.DeviceList[VersionStrip](Bus,address)
            else:
                self.Type=None
            if self.InUseBy!=None:
                self.Ident=VersionStrip
    
    def __init__(self, device = '/dev/spidev0.0', delay = 40, speed = 450000, bits = 8,Port=None,Server=None):
        """
            device = any SPI-Bus device in /dev, default /dev/spidev0.0
            delay  = SPI Bus delay between transactions in ms, default 0
            speed  = set the Bus Speed (Obsolete)
            bits   = Number of bits in a data word, default = 8
        """
        self.Port = Port
        self.Server=Server
        if self.Server != None:
            self.Transaction=self._NetTransaction
        else:
            if self.Port != None: # Init Server Thread
                self.ServerThread = threading.Thread(target=self.ListenerTread)
                self.ServerThread.start()
            self.Bits = c_uint8(bits)
            self.Speed = self.WriteSpeed
            self.Delay = c_uint16(delay)
            self.Device = device
            self.File = posix.open(self.Device, posix.O_RDWR)
            self.SetBits()
            self.SetSpeed()
        
    def Close(self):
        """ Close the filehandle to this bus """ 
        posix.close(self.File)

    def Transaction(self,OutBuffer, read = 0):
        """Do a SPI Transaction
        OutBuffer = mandatory String, containing chr(Address)+chr(Command)+chr(databyte 1)+....
        read      = Number of bytes to read from the SPI device
        """
        ReceiveBuffer = create_string_buffer(chr(0) * 0x80)
        TransmitBuffer= create_string_buffer(OutBuffer)
        Transaction = spi_ioc_transfer()
        Transaction.speed_hz = c_uint32(self.Speed)
        Transaction.tx_buf=addressof(TransmitBuffer)
        Transaction.rx_buf=addressof(ReceiveBuffer)
        Transaction.delay_usecs = self.Delay
        if read > 0 and self.Speed!= self.ReadSpeed:   # Slow down speed for reading
            Transaction.speed_hz = self.ReadSpeed
        elif read==0 and self.Speed!=self.WriteSpeed:
            Transaction.speed_hz = self.WriteSpeed
        if self.Speed != Transaction.speed_hz:
            self.Speed = Transaction.speed_hz
            self.SetSpeed()
        if read > len(OutBuffer):
            Transaction.len=read
        else:
            Transaction.len= len(OutBuffer)
        Transaction.bits_per_word = self.Bits
        Transaction.cs_change = 0
        Transaction.pad = 0
        ret = ioctl(self.File,SPI_IOC_MESSAGE(1), addressof(Transaction))
        return ret, ReceiveBuffer

    def SetBits(self):
        ret = ioctl(self.File, SPI_IOC_WR_BITS_PER_WORD, self.Bits);
        if ret == -1:
            print "can't set bits per word"

#    def GetBits(self):
#        ret = ioctl(self.File, SPI_IOC_RD_BITS_PER_WORD, addressof(self.Bits));
#        if ret == -1:
#            print "can't get bits per word"

    def SetSpeed(self):
#        ret = ioctl(self.File, SPI_IOC_WR_MAX_SPEED_HZ, addressof(self.Speed));
        ret = ioctl(self.File, SPI_IOC_WR_MAX_SPEED_HZ, struct.pack('I',self.Speed));
        if ret == -1:
            print "can't set max speed hz"

#    def GetSpeed(self):
#        ret = ioctl(lcd, SPI_IOC_RD_MAX_SPEED_HZ, addressof(self.Speed));
#        if ret == -1:
#            print "can't get max speed hz"


    #
    # TODO: change Transaction to _Bus.Read_String
    #
    def scan(self,Display=None,line=0):
        for i in range(0x00,0xFF,0x02):
            ret, buf = self.Transaction(chr(i+1)+chr(0x01),0x20)
            Identification =""
            for c in buf[2:]:
                if ord(c)==0: break
                if ord(c) in range(32,127):
                    Identification +=c
            if Identification != "":
                if i in self.Devices:
                    self.Devices[i].Ident=Identification.split(" ")[0].lower()
                else:
                    self.Devices[i]=SPI.Device(i,Ident=Identification,Bus=self)
            if Display!=None:
                ProgressBar(i,minval=0, maxval=0xFF , Display = Display, y=line)
                sleep(.05)

    def AddDevice(self,Address, InUseBy):
        self.Devices[Address]=SPI.Device(Address,InUseBy,Bus=self)
# -----------------------------------------------------------------------------
        
class BitWizardBase(object):
    DefaultAddress = 0x00
    
    def __init__(self, bus , address = None):
        if address == None:
            self.Address = self.DefaultAddress
        else:
            self.Address = address
        self.Bus = bus
        if self.Address in self.Bus.Devices:
            self.Bus.Devices[self.Address].InuseBy=self
        else:
            self.Bus.AddDevice(self.Address,InUseBy=self)

    # Return the Identification String of this Board
    def Ident(self):
        return self.Bus.Read_String(self.Address,Ident)

    # Retrun the Serial Number of this Board
    # TODO: use _NET method
    def Serial(self):
        ret,buf= self.Bus.Transaction(chr(self.Address+1)+chr(Serial),0x06)
        return struct.unpack(">L", buf[2:6])[0] 

    # Change the Address of this board, this can be done realtime and after calling this method
    # the objects instance will continue to communicate using the new address.
    def ChangeAddress(self, newaddress=None):
        if newaddress == None:
            newaddress = self.DefaultAddress
        if self.Address != newaddress:            
            self.Bus.Write_uInt8(self.Address,0xF1,0x55)
            self.Bus.Write_UInt8(self.Address,0xF2,0xAA)
            self.Bus.Write_uInt8(self.Address,0xF0,nwewaddress)
            self.Bus.Devices[newaddress]=self.Bus.Devices[self.Address]
            del self.Bus.Devices[self.Address]
            self.Address = newaddress
        

class BitWizardLcd(BitWizardBase):
    DefaultAddress = 0x82
    Cursor = "Off" #Blink, On

    # Set cursor to Position
    # x = position >= 0
    # y = line >=0
    def SetCursor(self,x,y):
        self.Bus.Write_uInt8(self.Address,0x11,32*y+x)

    # Clear Screen and set Cursor to (0,0)
    def Cls(self):
        self.Bus.Write_uInt8(self.Address,0x10,0x00)

    # Print text on current cursor position
    def Print(self,text = ""):
        self.Bus.Write_String(self.Address,0x00, text)

    # Print text on given position, see SetCursor
    def PrintAt(self,x=0,y=0,text=''):
        self.SetCursor(x,y)
        self.Print(text)

    # Set the Contrast of the LCD
    def Contrast(self, value=128):
        self.Bus.Write_uInt8(self.Address,Contrast,value)

    # Set the BackLight of the LCD
    def Backlight(self, value = 128):
        self.Bus.Write_uInt8(self.Address,Backlight,value)

    # Initialize the LCD Controller
    def Init(self):
        self.Bus.Write_uInt8(self.Address,InitLcd,value)

    # Send Command to LCD Controller
    def LcdCmd(self,cmd):
        self.Bus.Write_uInt8(self.Address,0x01,0x00)

    # Set Cursor Visible and make it blink or not
    def Cursor(self,on=True,blink=False):
        value = 8+4
        if on and blink:
            value+=1
        elif on and not blink:
            value+=2
        self.Bus.Write_uInt8(self.Address,0x01,value)

    # Set Cursor to the home position (0,0)
    def CursorHome(self):
        self.Bus.Write_uInt8(self.Address, 0x01, 0x02)
            
    # Define the:
    # char = character number 0 >= see LCD datasheet
    # data = char Bitmap see LCD Datasheet
    # TODO: This does NOT work and is for BitWizard.ui.ProgressBar
    # TODO: Change to make it functional
    def DefineChar(self,char, Data=[0,0,0,0,0,0,0,0]):
        self.Bus.Transaction(chr(self.Address)+chr(0x01)+chr(0x40))
        self.Bus.Transaction(chr(self.Address)+chr(0x00)+chr(0x00)+chr(0x00)+chr(0x00)+chr(0x00)+chr(0x00)+chr(0x00)+chr(0x00)+chr(0x00))
        self.Bus.Transaction(chr(self.Address)+chr(0x01)+chr(0x48))
        self.Bus.Transaction(chr(self.Address)+chr(0x00)+chr(0x10)+chr(0x10)+chr(0x10)+chr(0x10)+chr(0x10)+chr(0x10)+chr(0x10)+chr(0x10))
        self.Bus.Transaction(chr(self.Address)+chr(0x01)+chr(0x50))
        self.Bus.Transaction(chr(self.Address)+chr(0x00)+chr(0x18)+chr(0x18)+chr(0x18)+chr(0x18)+chr(0x18)+chr(0x18)+chr(0x18)+chr(0x18))
        self.Bus.Transaction(chr(self.Address)+chr(0x01)+chr(0x58))
        self.Bus.Transaction(chr(self.Address)+chr(0x00)+chr(0x1C)+chr(0x1C)+chr(0x1C)+chr(0x1C)+chr(0x1C)+chr(0x1C)+chr(0x1C)+chr(0x1C))
        self.Bus.Transaction(chr(self.Address)+chr(0x01)+chr(0x60))
        self.Bus.Transaction(chr(self.Address)+chr(0x00)+chr(0x1E)+chr(0x1E)+chr(0x1E)+chr(0x1E)+chr(0x1E)+chr(0x1E)+chr(0x1E)+chr(0x1E))
        self.Bus.Transaction(chr(self.Address)+chr(0x01)+chr(0x68))
        self.Bus.Transaction(chr(self.Address)+chr(0x00)+chr(0x1F)+chr(0x1F)+chr(0x1F)+chr(0x1F)+chr(0x1F)+chr(0x1F)+chr(0x1F)+chr(0x1F))
        
    # TODO: Investigate odd behaviour of LCD                                
    def DisplayMode(self, cursormove=True,displayshift=False):
        value=16
        if cursormove:
            value+=4
        elif displayshift:
            value+=4
        self.Bus.Write_uInt8(self.Address,0x01,value)

class BitWizardPushButtons(BitWizardBase):
    PushButtons = 0
    # Read All buttons for them being pressed right now
    # return an array of length self.PushButtons
    # with boolean values, True when being pressed
    def ReadAll(self):
        v =self.Bus.Read_uInt8(self.Address,0x10)
        Buttons = []
        for i in range(0,self.PushButtons):
            Buttons.append(v & 2**i == 2**i)
        return Buttons

    # Check One button
    # button = Buttonnumber >=0 < self.PushButtons
    # Returns True if the button is Pressed
    def ReadOne(self,button):
        return bool(self.Bus.Read_uInt8(self.Address, 0x40+button))

    # Read the Status of one butten, like ReadOne
    # Return is equal to: not self.ReadOne(button)
    def ReadOneInv(self,button):
        return bool(self.Bus.Read_uInt8(self.Address, 0x20+button))

    # Report if any button has been pressed since this method was last called.
    # Returns an array of length self.PushButtons with boolean values
    # True if that button has been pressed
    # Will reset the register
    def ReportPressed(self):
        v =self.Bus.Read_uInt8(self.Address,0x30)
        Buttons = []
        for i in range(0,self.PushButtons):
            Buttons.append(v & 2**i == 2**i)
        return Buttons


class IOPin():
    IO=0
    def __init__(self,Pin, parent):
        self.Pin=Pin
        self.Bus=parent.Bus
        self.Address = parent.Address
        self.IODevice=parent.IODevice
        if parent.PinConfig.has_key(Pin):
            if parent.PinConfig[Pin].has_key('property'):
                setattr(parent,parent.PinConfig[Pin]['property'],self)

    def PinMask(self):
        return (2**self.Pin) * self.IO


class DigitalIn(IOPin):
    def __init__(self,Pin,parent):
        IOPin.__init__(self,Pin,parent)
        
    def Get(self):
        value=False
        return value
    
class DigitalOut(IOPin):
    IO=1
    def __init__(self,Pin,parent):
        IOPin.__init__(self,Pin,parent)

    def Set(self,value):
        if value:
            onoff = 0x01
        else:
            onoff = 0x00
        self.Bus.Write_uInt8(self.Address,0x20+self.pin, onoff)

class AnalogIn(IOPin):
    ADChannel = None
    Vref = 5
    def __init__(self,Pin,parent):
        IOPin.__init__(self,Pin,parent)
        if parent.PinConfig.has_key(self.Pin):
            if parent.PinConfig[self.Pin].has_key("vref"):
                #print "Vref found"
                self.Vref = parent.PinConfig[self.Pin]["vref"]
        self.ADDevice  = parent
        self.ADChannel = self.ADDevice.ADCChannels
        self.ADDevice.ADCChannels+=1
        self.Config()

    def Config(self):
        CConfig = self.IODevice.ADCChannelConfig[self.Pin]
        if self.Vref ==1:
            CConfig += self.IODevice.AddFor1V1 
        self.Bus.Write_uInt8(self.Address,0x70+self.ADChannel,CConfig)
        
    # Sample the value according to this Boards Samples/Bitshift config
    # Retruns 16 bit value (0..65535)
    def Get(self):        
        return self.Bus.Read_uInt16(self.Address,0x68+self.Pin)
    
    # take one Sample without the Boards Bitshift Config
    # Returns 10 bit value (0..1023)
    def GetSample(self):        
        return self.Bus.Read_uInt16(self.Address,0x60+self.Pin)

    def __del__(self):
        self.ADDevice.ADCChannels-=1

class MCP9700(AnalogIn):
    VoltPerDegree = 0.010
    RefVoltage = 1.1000
    Vref=1    

    # Return Current Temperature value as float in Degree Celcius
    def GetCelcius(self):
        ADCMax = (self.ADDevice.ADSamples * 1023) /(2**self.ADDevice.ADBitshift)
        #if self.ADDevice.ADSamples == 1 and self.ADDevice.ADBitshift == 0:
        #    ADCMax=1023
        #else:
        #    ADCMax = 65535
        sample=self.Get()
        R = self.RefVoltage / ADCMax
        Volt = sample*R-.5        
        return Volt/self.VoltPerDegree

    # Return Current Temperature value as float in Degree Kelvin
    def GetKelvin(self):
        return self.GetCelcius() + 273.15

    # Return Current Temperature value as float in Degree Fahrenheit
    def GetFahrenheit(self):
        return self.GetCelcius()*1.8+32
        

class PWMOut(IOPin):
    IO=1

    # Set the value to be PWM encoded on the Pin
    def Set(self,value):
        self.Bus.Write_uInt8(self.Address,0x50+self.Pin,value)        

class IOPinBase():
    IODevice=ATTiny
    PinConfig = {}
    IOPins = 0
    ADCChannels = 0
    ADCChannelConfig = {}
    ADSamples = 4096
    ADBitshift = 6

    def __init__(self):
        self.Pins={}
        for p in range(self.IOPins):
            if self.PinConfig.has_key(p):
                self.Pins[p]=self.PinConfig[p]["device"](p,self)
            else:
                self.Pins[p]= DigitalIn(p,self)
        self.DoPinConfig()
        self.InitAnalog(self.ADSamples,self.ADBitshift)

    def DoPinConfig(self):
        mask = 0
        pwmmask = 0
        for p in range(self.IOPins):
            mask = mask | self.Pins[p].PinMask()
            if isinstance(self.Pins[p],PWMOut):
                pwmmask = pwmmask | 2**p
        self.SetInputOutput(mask,pwmmask)

    def SetPinConfig(self,pin, pintype, **kwargs):
        if self.Pins[pin]!=None:
            del self.Pins[pin]
        if self.PinConfig.has_key(pin):
            if self.PinConfig[pin].has_key('property'):
                delattr(self,self.PinConfig[pin]['property'])
            del self.PinConfig[pin]
        if not self.PinConfig.has_key(pin):
            self.PinConfig[pin] = kwargs           
        self.PinConfig[pin]["device"]=pintype
        c = self.ADCChannels
        self.Pins[pin]=pintype(pin,self)
        self.DoPinConfig()
        if c!= self.ADCChannels:
            self.Bus.Write_uInt8(self.Address,0x80,self.ADCChannel)

    def SetInputOutput(self, mask=0x00,pwmmask=0x00):
        self.Bus.Write_uInt8(self.Address,0x30,mask)
        self.Bus.Write_uInt8(self.Address,0x5F,pwmmask)
        
    def InitAnalog(self,ADSamples=None,ADBitshift=None):
        if self.ADCChannels > 0:
            if ADSamples!=None:
                self.ADSamples  = ADSamples
            if ADBitshift != None:
                self.ADBitshift = ADBitshift
            self.Bus.Write_uInt16(self.Address,0x81,self.ADSamples)
            self.Bus.Write_uInt16(self.Address,0x81,self.ADSamples)# there was a bug in old firmware, send twice
            self.Bus.Write_uInt8(self.Address,0x82,self.ADBitshift)
            self.Bus.Write_uInt8(self.Address,0x80,self.ADCChannels)
            

class DIO(BitWizardBase,IOPinBase):
    PinConfig={}
    IOPins = 7
    DefaultAddress = 0x84

    def __init__(self,bus, Address=None):
        BitWizardBase.__init__(self,bus,Address)
        IOPinBase.__init__(self)

    # Set All outputs according to bitmap, pin 0 is LSB
    def SetAllOutputs(self,value=0x00):
        self.Bus.Write_uInt8(self.Address,0x10,value)
        
SPI.DeviceList["spi_dio"]= DIO      
I2C.DeviceList["i2c_dio"]= DIO      
    

     

class LCD_16x2(BitWizardLcd):
    DefaultAddress = 0x82
    Width=16
    Height=2
SPI.DeviceList["spi_lcd"]= LCD_16x2      
I2C.DeviceList["i2c_lcd"]= LCD_16x2      


class LCD_20x4(BitWizardLcd):
    DefaultAddress = 0x94
    Width=20
    Height=4


class Servo(BitWizardBase):
    DefaultAddress= 0x86
    Servos = 7

    def SetPosition(self,servo = 1,position=128):
        self.Bus.Write_uInt8(self.Address,0x19+servo, position)
        
    def GetPosition(self,servo): 
        self.Bus.Read_uInt8(self.Address,0x19+servo)

SPI.DeviceList["spi_servo"]= Servo      
I2C.DeviceList["i2c_servo"]= Servo      


class PushButtons_4(BitWizardPushButtons):
    #DefaultAddress = 0x00
    PushButtons=4

class Ui_PushButtons(BitWizardPushButtons):
    PushButtons=6

class RPi_Ui_20x4(LCD_20x4,Ui_PushButtons,IOPinBase):
    IOPins=2
    DefaultAddress = 0x94
    IODevice = ATMega
    ADSamples = 4096
    ADBitshift = 6
    PinConfig={0:{"device":MCP9700,'property':'IntTemp'},1:{"device":AnalogIn,"vref":1,'property':'ExtAnalog'}}

    def __init__(self,*args,**kwargs):
        BitWizardBase.__init__(self,*args,**kwargs)
        IOPinBase.__init__(self)
    
SPI.DeviceList["spi_rpi_ui"]= RPi_Ui_20x4     


class RPi_Ui_16x2(LCD_20x4,Ui_PushButtons, IOPinBase):
    DefaultAddress = 0x94
    IOPins=2
    DefaultAddress = 0x94
    IODevice = ATMega
    ADSamples = 4096
    ADBitshift = 6
    PinConfig={0:{"device":MCP9700,'property':'IntTemp'},1:{"device":AnalogIn,"vref":1,'property':'ExtAnalog'}}

    def __init__(self,*args,**kwargs):
        BitWizardBase.__init__(self,*args,**kwargs)
        IOPinBase.__init__(self)

#SPI.DeviceList["spi_rpi_ui"]= RPi_Ui_16x2     


class LED7Segment(BitWizardBase):
    DefaultAddress = 0x96

    def SetBitmap4(self,D1=0,D2=0,D3=0,D4=0):
        self.Bus.Write_uInt8s(self.Address,0x10,D1,D2,D3,D4)

    def SetBitmap1(self,char, value=0):
        self.Bus.Write_uInt8(self.Address,0x19+char,value)

    def SetHex4(self,D1=0,D2=0,D3=0,D4=0):
        self.Bus.Write_uInt8s(self.Address,0x11,D1,D2,D3,D4)
        
    def SetHex1(self,char, value=0):
        self.Bus.Write_uInt8(self.Address,0x30+char,value)


    def BottomDot(self,on=True):
        if on:
            value=0x01
        else:
            value=0x00
        self.Bus.Write_uInt8(self.Address,0x40,value)
        
    def UpperDot(self,on=True):
        if on:
            value=0x01
        else:
            value=0x00
        self.Bus.Write_uInt8(self.Address,0x41,value)

    def BothDots(self,on=True):
        if on:
            value=0x01
        else:
            value=0x00
        self.Bus.Write_uInt8(self.Address,0x42,value)

    #TODO : Fix
    def GetBitmap4(self,D1=0,D2=0,D3=0,D4=0):
        return self.Bus.Transaction(chr(self.Address)+chr(0x10)+chr(D1))
    #TODO : Fix
    def GetBitmap1(self,chart):
        return self.Bus.Transaction(chr(self.Address)+chr(0x19+char))
SPI.DeviceList['spi_7segment']=LED7Segment



class Relay(BitWizardBase,IOPinBase):
    DefaultAddress = 0x8E
    IOPins = 2
    PinConfig = {0:{'device':DigitalOut},1:{'device':DigitalOut}}

def __init__(self,bus, Address=None):
        BitWizardBase.__init__(self,bus,Address)
        IOPinBase.__init__(self)

SPI.DeviceList["spi_relay"]= Relay      
I2C.DeviceList["i2c_relay"]= Relay      


class BigRelay(BitWizardBase,IOPinBase):
    DefaultAddress = 0x9E
    IOPins = 6
    PinConfig = {}
    PinConfig[0]={'device':DigitalOut}
    PinConfig[1]={'device':DigitalOut}
    PinConfig[2]={'device':DigitalOut}
    PinConfig[3]={'device':DigitalOut}
    PinConfig[4]={'device':DigitalOut}
    PinConfig[5]={'device':DigitalOut}

    def __init__(self,bus, Address=None):
        BitWizardBase.__init__(self,bus,Address)
        IOPinBase.__init__(self)


SPI.DeviceList["spi_bigrelay"]= BigRelay      
I2C.DeviceList["i2c_bigrelay"]= BigRelay      


class Fet3(BitWizardBase,IOPinBase):
    DefaultAddress = 0x8A
    IOPins = 3
    PinConfig = {}
    PinConfig[0] = {'device':PWMOut}
    PinConfig[1] = {'device':PWMOut}
    PinConfig[2] = {'device':PWMOut}

    def __init__(self,bus, Address=None):
        BitWizardBase.__init__(self,bus,Address)
        IOPinBase.__init__(self)

SPI.DeviceList["spi_3fet"]= Fet3      
I2C.DeviceList["i2c_3fet"]= Fet3      

class StepperMotor:

    class StepperPin(IOPin):
        IO=1

    def StepperInit(self,StepAngle=1.0,Reduction=1.0, North=0, StepDelay=200 ,CurrentPosition=None,Reverse=False):
        self.StepAngle = StepAngle
        self.Reduction = Reduction
        self.Reverse = Reverse
        self.North = North
        for p in range(4):
            self.SetPinConfig(p,StepperMotor.StepperPin)
        self.SetStepDelay(StepDelay)
        if CurrentPosition!=None:
            self.SetCurrentPosition(CurrentPosition)
            
    def DegreeToSteps(self,Degree):
        return int(round(Degree*(self.Reduction/self.StepAngle/2)))

    def StepsToDegree(self,Steps):
        return int(round(Steps/(self.Reduction/self.StepAngle/2)))
    
    def SetCurrentPosition(self,pos):
        if self.Reverse: pos*=-1
        self.Bus.Transaction(chr(self.Address)+chr(0x40)+struct.pack('@l',pos))

    def GetCurrentPosition(self):
        r,v = self.Bus.Transaction(chr(self.Address+1)+chr(0x40),0x06)
        if self.Reverse:
           r=-1
        else:
            r=1
        return r*struct.unpack('@l', v[2:6])[0]

    def GetCurrentDegree(self):
        return self.StepsToDegree(self.GetCurrentPosition())

    def SetTargetPosition(self,pos):
        if self.Reverse: pos*=-1
        self.Bus.Transaction(chr(self.Address)+chr(0x41)+struct.pack('@l',pos))

    def GetTargetPosition(self):
        if self.Reverse:
           r=-1
        else:
            r=1
        return r*struct.unpack('@l',z.Bus.Transaction(chr(z.Address+1)+chr(0x41),0x06)[1][2:6])[0]

    def SetTargetDegree(self,Degree):
        self.SetTargetPosition(self.DegreeToSteps(Degree))

    def GetTargetDegree(self):
        return self.StepsToDegree(self.GetTargetPosition())

    def SetRelativePosition(self,pos):
        if self.Reverse: pos*=-1
        self.Bus.Transaction(chr(self.Address)+chr(0x42)+struct.pack('@l',pos))

    def SetRelativeDegree(self,Degree):
        self.SetRelativePosition(self.DegreeToSteps(Degree))

    def SetStepDelay(self,delay=200):
        self.Bus.Transaction(chr(self.Address)+chr(0x43)+chr(delay))

    def GetStepDelay(self):
        self.Bus.Transaction(chr(self.Address+1)+Chr(0x43),0x3)


class Fet7(BitWizardBase,IOPinBase,StepperMotor):
    DefaultAddress = 0x88
    IOPins = 7
    PinConfig={}
    PinConfig[0] = {'device':PWMOut}
    PinConfig[1] = {'device':PWMOut}
    PinConfig[2] = {'device':PWMOut}
    PinConfig[3] = {'device':PWMOut}
    PinConfig[4] = {'device':PWMOut}
    PinConfig[5] = {'device':PWMOut}
    PinConfig[6] = {'device':PWMOut}

    def __init__(self,bus, Address=None):
        BitWizardBase.__init__(self,bus,Address)
        IOPinBase.__init__(self)

                             
SPI.DeviceList["spi_7fet"]= Fet7      
I2C.DeviceList["i2c_7fet"]= Fet7      


