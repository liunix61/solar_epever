"""
License: see license_gpl-3.0.txt
"""
import board
import os
import busio
import digitalio
import time
import binascii
from struct import *
from modbusrtu import ModBusRTU
import adafruit_logging as logging
import json

class EPEVER(ModBusRTU):
    LOGO="""
 _____  _____  _____  _____  _____  _____ 
|   __||  _  ||   __||  |  ||   __|| __  |
|   __||   __||   __||  |  ||   __||    -|
|_____||__|   |_____| \___/ |_____||__|__|                                                                                                                               
    """
    VERSION = os.getenv('EPEVER_VERSION')
    
    # {<functioncode> : {<register> : {<type>, <unit>, <scale>, <format>}}
    fCode = {
        # Read Holding Register (0x03) and Write Multiple Holding Register (0x10)
        # Setting Parameter (Read and Write)
        "03": {
            "9000": {"identifier": "E1", "unit":"identifier", "convert":"dec", "scale":1, "quantity":1, "fmt":'>BBBHxx', "info":""},
            "9001": {"identifier": "E2", "unit":"'Ah", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx', "info":""},
            "9002": {"identifier": "E3", "unit":"mV", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx', "info":""},
            
        },
        # Read Input Register(0x04)
        "04" : {
            # Rated datum (read-only)
            "3000": {"identifier": "A1", "unit":"V", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx', "info":"PV array rated voltage"}, # 
            "3001": {"identifier": "A2", "unit":"A", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx', "info":"PV array rated current"}, # 
            "3002": {"identifier": "A3", "unit":"W", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx', "info":"PV array rated power (L=16bit, H=16Bit at 0x3003)"}, # 
            "3004": {"identifier": "A5", "unit":"V", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx', "info":"Rated voltage to bat"}, # 
            "3005": {"identifier": "A6", "unit":"A", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx', "info":"Rated current to bat"}, # 
            "3006": {"identifier": "A7", "unit":"W", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx', "info":"Rated power to bat (L & H (0x3007)"}, # 
            "3008": {"identifier": "A9", "unit":"-", "convert":"bin", "scale":100, "quantity":1, "fmt":'>BBBHxx', "info":"Connect/disconnect"}, # 
            "300E": {"identifier": "A10", "unit":"W", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx', "info":"rated current of load"}, #
            # real-time datum (read-only)
            "3100": {"identifier": "B1", "unit":"V", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx', "info":"Solar charger PV-voltage"}, # 
            "3101": {"identifier": "B2", "unit":"A", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx', "info":"Solar charger PV-current"}, # 
            "3102": {"identifier": "B3", "unit":"W", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx', "info":"Solar PV-Power L (0x3103 PV-Power H)"},	# 
            "3106": {"identifier": "B7", "unit":"W", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx', "info":"Solar Bat-Power L (0x3107 Bat-Power H)"},	# 
            "310C": {"identifier": "B13", "unit":"V", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx', "info":"Load voltage"}, # 
            "310D": {"identifier": "B14", "unit":"A", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx', "info":"Load current"}, # 
            "310E": {"identifier": "B15", "unit":"W", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx', "info":"Load Power L (0x310F H)"}, # 
            "3110": {"identifier": "B17", "unit":"°C", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx', "info":"Bat Temp"}, # 
            "3111": {"identifier": "B18", "unit":"°C", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx', "info":"Temp inside charger"}, # 
            "311A": {"identifier": "B27", "unit":"%%", "convert":"dec", "scale":1, "quantity":1, "fmt":'>BBBHxx', "info":"Bat SOC"}, # 
            "311B": {"identifier": "B28", "unit":"°C", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx', "info":"Bat Temp remote sensor"}, # 
            "311D": {"identifier": "B30", "unit":"V", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx', "info":"current system rated voltage"}, # 

            # Real-time status (read only)
            "3200": {"identifier": "C1", "unit":"-", "convert":"bin", "scale":1, "quantity":1, "fmt":'>BBBHxx', "info":"Bat Status 16Bit-Field"}, # 
            "3201": {"identifier": "C2", "unit":"-", "convert":"bin", "scale":1, "quantity":1, "fmt":'>BBBHxx', "info":"Charging status 16Bit-Field"}, # 
            "3202": {"identifier": "C27", "unit":"-", "convert":"bin", "scale":1, "quantity":1, "fmt":'>BBBHxx', "info":"Discharging status 16Bit-Field"}, # 

            # Statistical prameters (read only)
            "3300": {"identifier": "D0", "unit":"V", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx', "info":"Max PV volt today"}, 	# 
            "3301": {"identifier": "D1", "unit":"V", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx', "info":"Min PV vol todday"}, 	# 
            "3302": {"identifier": "D2", "unit":"V", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx', "info":"Max bat volt today"}, 	# 
            "3303": {"identifier": "D3", "unit":"V", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx', "info":"Min bat volt today"}, 	# 
            "3304": {"identifier": "D4", "unit":"kWh", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx', "info":"consumed energy today L(D4) & H (D5)"}, 	# 
            "3306": {"identifier": "D6", "unit":"kWh", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx', "info":"consumed energy month L(D8) H(D9)"},	# 
            "3308": {"identifier": "D8", "unit":"kWh", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx', "info":"consumed energy year L(D8) H(D9)"},	# 
            "330A": {"identifier": "D10", "unit":"kWh", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx', "info":"consumed energy total L(D10) H(D11)"},	# 
            "330C": {"identifier": "D12", "unit":"kWh", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx', "info":"generated energy today L(D12) H(D13)"},	# 
            "330E": {"identifier": "D14", "unit":"kWh", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx', "info":"generated energy month L(D14) H(D15)"},	# 
            "3310": {"identifier": "D16", "unit":"kWh", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx', "info":"generated energy year L(D16) H(D17)"},	# 
            "3312": {"identifier": "D18", "unit":"kWh", "convert":"dec", "scale":100, "quantity":2, "fmt":'>BBBHHxx', "info":"generated energy total L(D18) H(D19)"},	# 
            "331A": {"identifier": "D26", "unit":"V", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx', "info":"percentage of battery's remaining capacity"},
            "331B": {"identifier": "D27", "unit":"A", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx', "info":"attery temperature measured by remote temperature sensor"},
            "331C": {"identifier": "D28", "unit":"V", "convert":"dec", "scale":100, "quantity":1, "fmt":'>BBBHxx', "info":"Current system rated voltage."},
            }
        }
        
    def __init__(self,uart, slaveID=1, demo=False):
        super().__init__(uart,slaveID,demo)
        self.log = logging.getLogger('EPEVER')        
        self.log.setLevel(os.getenv('EPEVER_LOGLEVEL'))
        self.log.info(self.LOGO)
        self.log.info(self.VERSION)
        self.log.info(f"EPVER connected via UART={uart}")
        self.log.info(f"EPVER SlaveID={slaveID}")

       
    def getFunctionCodeList(self):
        """ return a key list from all function codes """
        return self.fCode.keys()
    
    def getRegisterList(self, fcode):
        """ return key list from all register for this fcode """
        if fcode in self.fCode:
            return self.fCode[fcode]
        
    def _registerAvailable(self, fcode, register):
        """ check if fcode and register are configured. If not return None """
        if fcode in self.fCode:
            address = str(hex(register)[2:]).upper()
            self.log.debug(f"_registerAvailable: fcode {fcode} found, {address}")
            if address in self.fCode[fcode]:
                return self.fCode[fcode][address]
            else:
                self.log.error(f"Register '{address}' not configured - ignore")
        return None
    
    def _convert2Bin(self,value):
        """ convert a value into its binary representation """
        convert = f"{bin(int(value))[2:]:0>16}" # remove 0b, create a 16bit string value
        return convert	
    
    def _convertData(self, fcode, register, rcfg, data):
        """
        convert data into a human readable dict
        
        Arguments:
        fcode		current used function code
        register	current used register
        rcfg		configuration data for used register
        data		data list to convert
        
        Return
        converted 	dictionary {"fcode":<fcode>, "register": <register>, "len":<len>, "value":<value>, "unit":<unit>, "info":<info>}}
        """
        converted = {'fcode':'', "register":"", "len":0, "identifier":"", "unit":"", "info":"", "value":0}
        try:
            data = data[fcode]
            value = float(int(data[3]) / rcfg["scale"])
            converted["fcode" ]		= fcode
            converted["register"] 	= f"{register:04x}"
            converted["len"]		= int(data[2])
            converted["identifier"] = rcfg["identifier"]
            converted["unit"] 		= rcfg["unit"]
            converted["info"] 		= rcfg["info"]
            if rcfg["convert"] == "bin":
                binary = self._convert2Bin(data[3])
                converted["value"] 		= binary
            else:
                converted["value"] 		= value

            #print (f"EPEVER >>>> {converted}")
            #print (f"**** {data}")
            self.log.debug(f"_convertData() => {str(converted)}")
        except:
            converted["info"] = "error in epever.py Z130-143" 
        self.log.debug(f"_convertData() => {str(converted)}")
        
        return converted
        
    def read(self, fcode, register):
        """
        Read a register from EPEVER
        
        Arguments:
        fcode		string 		"01", "02", "03", "04"
        register	hexword		register address as hex value (e.g. 0x3100)
        
        Return:
        raw,converted		tuple	(raw list, converted-dict)
                            converted-dict => {"register":"<type>":"<value", "unit":<unit>}
        
        """
        regcfg = self._registerAvailable(fcode, register)
        if regcfg != None:
            converted = {}
            self.log.debug("send data....")
            nbytes, data = self.send(func=fcode,
                                     register=register,
                                     quantity=regcfg['quantity'],
                                     swapBytes=True
                                     )
            self.log.info(f"SEND:\t\t{data}\t({nbytes})")
            raw = self.receive(returnByteArray=True)
            self.log.debug(f"raw bytearray {raw} ({len(raw)}); convert with fmt='{regcfg['fmt']}'")
            if len(raw) >= 7:
                decoded = self.decode(raw,fcode, fmt=regcfg['fmt'])
                self.log.debug (f"RECEIVE:\n{raw} | {decoded}")
                converted = self._convertData(fcode, register, regcfg, decoded)
                self.log.info (f"RECEIVE:\nraw:\t\t{raw}\ndecoded:\t{decoded}\nconverted:\t{str(converted)}")
                return raw, converted
        return None, None
    # TX  01 04 31 00 00 01 3F 36 	(RTU-Software)
    #     01 04 31 00 00 01 3f 36 	(Pico)
    # RX  01 04 02 0a 81 7f f0 		(0x0A81 = 26.89V)
    
    def write (self, fcode, register, data):
        self.log.warning ("not implemented yet")
        return None
    
# for Test purposes please remove comment char

#EPEVER_TX = eval(f"board.{os.getenv('UART1_TX')}")
#EPEVER_RX = eval(f"board.{os.getenv('UART1_RX')}")
#uart1 = busio.UART(EPEVER_TX, EPEVER_RX, baudrate=115200)

#epever = EPEVER(uart=uart1, slaveID=1)
#modbus = ModBusRTU(uart1)

#msg = """\n
#**********************************************************
#EPEVER ModBus - READ InputRegister (0x04) - TEST
#**********************************************************\n
#"""
#print (msg)

#p = epever.read("04", 0x3200)
#time.sleep(2)
    
#while True:
#    print ("******************************************************")
#    for fc in sorted(epever.getFunctionCodeList()):
#        print (f">>>>>>>>> FCode '{fc}'")
#        for reg in sorted(epever.getRegisterList(fc)):
#            print (f"---------- Register '{reg}'")
#            p = epever.read(fc, int(hex(int(reg,16)),16))   
#            time.sleep(2)
#    


#----------------------------------
# below only special test scenarios
#----------------------------------

# modbus = ModBusRTU(None,1)
# 
# d0 = bytearray("0103310000018AF6")
# d1 = bytearray("010100010001AC0A")
# d2 = bytearray("0104310000013F36")
# d3 = bytearray("0103311D00011AF0")
# 
# p, data = modbus.send("03",0x3100, 0x1)
# print (f"Bytes written: {p}")
# p, data  = modbus.send("03",0x311D, 0x1)
# print (f"Bytes written: {p}")
# p, data  = modbus.send("04",0x3100, 0x1)
# print (f"Bytes written: {p}")
# p, data  = modbus.send("04",0x0031, 0x1)
# print (f"Bytes written: {p}")
# 
# p, data  = modbus.send("03",0x3100, 0x1)
# r = modbus.receive()
# print (f"Send: {p} / {data} -> Receive: {r}")
# decoded = modbus.decode(data)
# print (f"Decoded data {decoded}")
# decoded = modbus.decode(r, fmt=">BBBBHHxx")
# print (f"Decoded data {decoded}")
# #crc = epever.crc16(d1,True)
# #print (f"CRC: {crc:0}")
# 
# #crc = epever.crc16(d2,True)
# #print (f"CRC: {hex(crc).upper()}")
# 
# #crc = epever.crc16(d3,True)
# #print (f"CRC: {hex(crc).upper()}")
# 


