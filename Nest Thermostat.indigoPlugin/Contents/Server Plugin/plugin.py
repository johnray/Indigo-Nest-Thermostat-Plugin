#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2012, Perceptive Automation, LLC. All rights reserved.
# http://www.perceptiveautomation.com

import os
import sys
import random
import urllib2
import urllib
import time
# Need json support; Use "simplejson" for Indigo support
try:
	import simplejson as json
except:
	import json

# Time limit for the cache to exist between requiring an update
NEST_CACHE_REFRESH_TIMEOUT=5

# Time limit between auth token refreshes
NEST_AUTH_REFRESH_TIMEOUT=3600

# Maximum number of retries before deciding that sending a command failed
NEST_MAX_RETRIES=5

# Time to wait between retries (in seconds)
NEST_RETRY_WAIT=0.1

# Simple constant mapping for fan, heat/cool type, etc.
NEST_FAN_MAP={'auto on':"auto",'on': "on", 'auto': "auto", 'always on': "on", '1': "on", '0': "auto"}
NEST_AWAY_MAP={'on':True,'away':True,'off':False,'home':False,True:True, False:False}
NEST_HEAT_COOL_MAP={'cool':'cool','cooling':'cool','heat':'heat','heating':
					'heat','range':'range','both':'range','auto':"range",'off':'off'}

# Nest URL Constants. These shouldn't be changed.
NEST_URLS="urls"
NEST_TRANSPORT_URL="transport_url"
NEST_LOGIN_URL="https://home.nest.com/user/login"
NEST_STATUS_URL_FRAGMENT="/v2/mobile/user."
NEST_SHARED_URL_FRAGMENT="/v2/put/shared."
NEST_DEVICE_URL_FRAGMENT="/v2/put/device."
NEST_STRUCTURE_URL_FRAGMENT="/v2/put/structure."

# Nest Data Constants. These shouldn't be changed.
NEST_USER_ID="userid"
NEST_ACCESS_TOKEN="access_token"
NEST_DEVICE_DATA="device"
NEST_SHARED_DATA="shared"
NEST_STRUCTURE_DATA="structure"
NEST_STRUCTURE_NAME="name"
NEST_DEVICE_NAME="name"

# Nest Status Constants. These shouldn't be changed, but if the module is expanded,
# new constants can be placed here.
NEST_CURRENT_TEMP="current_temperature"
NEST_CURRENT_HUMIDITY="current_humidity"
NEST_CURRENT_FAN_MODE="fan_mode"
NEST_TARGET_TEMP="target_temperature"
NEST_TARGET_CHANGE_PENDING="target_change_pending"
NEST_HEAT_COOL_MODE="target_temperature_type"
NEST_RANGE_TEMP_HIGH="target_temperature_high"
NEST_RANGE_TEMP_LOW="target_temperature_low"
NEST_HEAT_ON="hvac_heater_state"
NEST_AC_ON="hvac_ac_state"
NEST_FAN_ON="hvac_fan_state"
NEST_TEMP_SCALE="temperature_scale"
NEST_AWAY="away"

class NestThermostat:
	
	def __init__(self, username, password, name, location):
		"""Initialize a new Nest thermostat object
		
				Arguments:
					username - username for Nest website
					password - password for Nest website
					name - The name of the Nest you want to control (as entered on nest.com)
					location - The location of the Nest you want to control (as entered on nest.com)
		"""
		self._username=username
		self._password=password
		self._nest_name=name
		self._structure_name=location
		self._refresh_auth()
		self._refresh_status()
	
	def _refresh_auth(self):
		"""Refreshes the Nest login token.
		
				The Nest site authentication token expires after a set period of time. This
				method refreshes it. All methods in this class automatically call this method
				after NEST_AUTH_REFRESH_TIMEOUT seconds have passed, so calling it explicitly
				is unneeded.
		"""
		send_data=urllib.urlencode({"username":self._username,"password":self._password})
		init_data=json.loads((urllib2.urlopen(urllib2.Request(NEST_LOGIN_URL,send_data))).read())

		# Store time of refresh of the auth token
		self._last_auth_refresh=time.time()

		# Pieces needed for status and control
		self._transport_url=init_data[NEST_URLS][NEST_TRANSPORT_URL]
		access_token=init_data[NEST_ACCESS_TOKEN]
		user_id=init_data[NEST_USER_ID]

		# Setup the header and status URL that will be needed elsewhere in the class
		self._header={"Authorization":"Basic "+access_token,"X-nl-protocol-version": "1"}
		self._status_url=self._transport_url+NEST_STATUS_URL_FRAGMENT+user_id
		
		# Invalidate the cache
		self._cached=False

	def _refresh_status(self):
		"""Refreshes the Nest thermostat data.
		
				This method grabs the current data from the Nest website for use with the
				rest of the class methods. If NEST_AUTH_REFRESH_TIMEOUT seconds haven't yet
				passed, the method doesn't do anything (ie. the existing data remains cached).
				
				This method is called automatically by other methods that return information from
				the Nest, so calling it explicitly is unneeded.
		"""
		# Before doing anything, check to see if the auth token should be refreshed
		if ((time.time()-self._last_auth_refresh)>NEST_AUTH_REFRESH_TIMEOUT):
			self._refresh_auth()
		# Refresh the status data, if needed
		if (not self._cached or (time.time()-self._last_update>NEST_CACHE_REFRESH_TIMEOUT)):
			self._cached=True
			self._last_update=time.time()
			self._status_data=json.loads((urllib2.urlopen(urllib2.Request(self._status_url,headers=self._header))).read())
			# Loop through structures to find the named structure and build a lookup table
			structures=self._status_data[NEST_STRUCTURE_DATA]
			self._nest_structures=dict()
			for key in structures.keys():
				self._nest_structures[structures[key][NEST_STRUCTURE_NAME]]=key
			# Look through serial numbers to find Nest names and build a lookup table
			serials=self._status_data[NEST_SHARED_DATA]
			self._nest_serials=dict()
			for key in serials.keys():
				self._nest_serials[serials[key][NEST_DEVICE_NAME]]=key
	
			# Use this to set the serial and structure (location) instance variables and construct the URLs.  
			# I'd rather do this earlier, but letting the user refer to the Nest (and its location) by name
			# is worth it.
			
			self._serial=self._nest_serials[self._nest_name]
			self._structure=self._nest_structures[self._structure_name]
	
			# Setup the remaining URLs for the class
			self._shared_url=self._transport_url+NEST_SHARED_URL_FRAGMENT+self._serial
			self._device_url=self._transport_url+NEST_DEVICE_URL_FRAGMENT+self._serial
			self._structure_url=self._transport_url+NEST_STRUCTURE_URL_FRAGMENT+self._structure
	
	def	_get_attribute(self,attribute):
		"""Returns the value of a Nest thermostat attribute, such as the current temperature.
		
				Arguments:
					attribute - The attribute string to retrieve
		"""
		try:
			return self._status_data[NEST_DEVICE_DATA][self._serial][attribute]
		except:
			try:
				return self._status_data[NEST_SHARED_DATA][self._serial][attribute]
			except:
				return self._status_data[NEST_STRUCTURE_DATA][self._structure][attribute]
			
	def _apply_temp_scale(self,temp):
		"""Given a temperature, returns the temperature in F or C depending on the Nest's settings.
		
				This method is used for getting the appropriate temperature reading when retrieving settings
				from the Nest. 
				
				For sending temperatures values, use _apply_temp_scale_c() to convert them (if
				needed) to C.
		
				Arguments:
					temp - The temperature (float) to convert (if needed)
		"""
		if (self.temp_scale_is_f()):
			return round(temp*1.8+32)
		else:
			return round(temp)
			
	def _send_command(self,command,url):
		"""Attempts to send a command to the Nest thermostat via the Nest website.
		
				This method accepts a command string (JSON data) and attempts to send it to the Nest
				site. If the transmission fails, it fails silently since error checking must be handled
				by validating that a change has been made in the Nest attributes.
		
				Arguments:
					command - JSON formatted data to send to the Nest site
					url - The URL where the data should be posted
		"""
		discard_me=""
		try:
			discard_me=urllib2.urlopen(urllib2.Request(url,command,headers=self._header)).read()
		except:
			# Do nothing
			pass
		return discard_me

	def _apply_temp_scale_c(self,temp):
		"""Given a temperature, returns the temperature in C, if needed depending on the Nest's settings.
		
				This method is used when sending data to the Nest. The Nest expects values to be sent in C
				regardless of its internal temperature scale setting. This method is used by the class to 
				automatically convert temperatures (when sending) to C if needed. 
				
				For reading temperatures values, use _apply_temp_scale_() to convert them (if needed) to F.
		
				Arguments:
					temp - The temperature (float) to convert (if needed)
		"""
		if (self.temp_scale_is_f()):
			return (temp-32)/1.8
		else:
			return temp
	
	def get_temp(self):
		"""Returns the current temperature (float) reported by the Nest."""
		# Update the current status
		self._refresh_status()
		return self._apply_temp_scale(self._get_attribute(NEST_CURRENT_TEMP))
		
	def get_humidity(self):
		"""Returns the current humidity (integer representing percentage) reported by the Nest."""
		# Update the current status
		self._refresh_status()
		return round(self._get_attribute(NEST_CURRENT_HUMIDITY))
		
	def get_fan_mode(self):
		"""Returns 'auto' if the fan turns on automatically, or 'on' if it is always on."""
		# Update the current status
		self._refresh_status()
		return (NEST_FAN_MAP[self._get_attribute(NEST_CURRENT_FAN_MODE)])
		
	def get_target_temp(self):
		"""Returns the temperature (float) that the Nest is trying to reach."""
		# Update the current status
		self._refresh_status()
		return self._apply_temp_scale(self._get_attribute(NEST_TARGET_TEMP))
		
	def target_temp_change_is_pending(self):
		"""Returns True if the Nest is trying to set a new target temperature."""
		# Update the current status, this is time sensitive so invalidate the cache
		self._cached=False
		self._refresh_status()
		return self._get_attribute(NEST_TARGET_CHANGE_PENDING)
		
	def get_temp_scale(self):
		"""Returns 'F' if the Nest is set to Farenheit, 'C' if Celcius."""
		# Get temperature scale (F or C) from Nest
		self._refresh_status()
		return self._get_attribute(NEST_TEMP_SCALE)
		
	def get_range_temps(self):
		"""Returns a dictionary with the 'high' and 'low' temperatures (float) set for the Nest.
		
				The range temperatures are only used when the nest is in auto heat/cool mode. The
				dictionary keys for the method, in case it wasn't obvious, are 'high' for the upper
				temperature limit (how hot can it get), and 'low' for the low limit (how cold).
		"""
		# Update the current status
		self._refresh_status()
		return {'low':self._apply_temp_scale(self._get_attribute(NEST_RANGE_TEMP_LOW)),
				'high':self._apply_temp_scale(self._get_attribute(NEST_RANGE_TEMP_HIGH))}
		
	def get_heat_cool_mode(self):
		"""Returns 'cool' when Nest in AC mode, 'heat' in heating mode, and 'auto' in heat/cool mode.
	
				Returns a string that identifies the mode that the Nest is operating in. AC is 'cool', 
				heating is 'heat', and maintaining a temperature range is 'auto'. If the system is off, 'off'
				is returned.
				
				Note that the value returned is passed through a dictionary so it can be mapped to 
				alternative strings. This was included for ease of integration with Indigo and can just
				be ignored for general use.
		"""
		# Update the current status
		self._refresh_status()
		return NEST_HEAT_COOL_MAP[self._get_attribute(NEST_HEAT_COOL_MODE)]
		
	def temp_scale_is_f(self):
		"""Returns True if the Nest temperature scale is Fahrenheit, False if Celcius"""
		if (self.get_temp_scale()=="F"):
			return True
		else:
			return False
		
	def fan_is_on(self):
		"""Returns True if the fan is currently on."""
		# Update the current status
		self._refresh_status()
		return self._get_attribute(NEST_FAN_ON)

	def heat_is_on(self):
		"""Returns True if the heat is currently on."""
		# Update the current status
		self._refresh_status()
		return self._get_attribute(NEST_HEAT_ON)

	def ac_is_on(self):
		"""Returns True if the AC is currently on."""
		# Update the current status
		self._refresh_status()
		return self._get_attribute(NEST_AC_ON)
		
	def away_is_active(self):
		"""Returns True if the Nest is in 'away' mode."""
		# Update the current status
		self._refresh_status()
		return self._get_attribute(NEST_AWAY)
		
	def set_fan_mode(self,command='auto'):
		"""Sets the Nest fan mode to 'on' (always on) or 'auto' based on the provided command string.
	
				Arguments:
					command - A string representing the Nest fan mode. 'on' for always on, 'auto' for auto.
				
				Note that the value sent to the Nest is passed through a dictionary so it can be mapped to 
				alternative strings. This was included for ease of integration with Indigo and can just
				be ignored for general use.
		"""
		self._refresh_status()
		send_data=json.dumps({NEST_CURRENT_FAN_MODE:NEST_FAN_MAP[command]})
		retry_count=0
		while (retry_count<NEST_MAX_RETRIES):
			self._cached=False
			self._send_command(send_data,self._shared_url)
			retry_count=retry_count+1
			if (NEST_FAN_MAP[command]==self.get_fan_mode()):
				return True
			time.sleep(NEST_RETRY_WAIT)
		return False
		
	def set_away_state(self,command='off'):
		"""Sets the Nest away state 'on' (away) or 'off' (home) based on the provided command string.
	
				Arguments:
					command - A string representing the away state. 'on' for away, 'off' for home.
				
				Note that the value sent to the Nest is passed through a dictionary so it can be mapped to 
				alternative strings. In this case, I liked 'on' and 'off' better than true or false.
		"""
		self._refresh_status()
		send_data=json.dumps({NEST_AWAY:NEST_AWAY_MAP[command]})
		retry_count=0
		while (retry_count<NEST_MAX_RETRIES):
			self._cached=False
			self._send_command(send_data,self._structure_url)
			retry_count=retry_count+1
			if ((NEST_AWAY_MAP[command]==True and self.away_is_active()) or
				(NEST_AWAY_MAP[command]==False and not self.away_is_active())):
				return True
			time.sleep(NEST_RETRY_WAIT)
		return False
			
	def set_heat_cool_mode(self,command='cool'):
		"""Sets the Nest thermostat mode to 'cool' (AC), 'heat' (heating), 'range' (auto heat/cool), or 'off'.
	
				Arguments:
					command - A string representing the Nest fan mode. 'cool' for AC, 'heat' for heating, 
							'range' for maintaining a temperature range, or 'off' to turn the HVAC system off.
							Default is 'cool' because I hate the heat.
				
				Note that the value sent to the Nest is passed through a dictionary so it can be mapped to 
				alternative strings. This was included for ease of integration with Indigo and can just
				be ignored for general use.
		"""
		self._refresh_status()
		send_data=json.dumps({NEST_HEAT_COOL_MODE:NEST_HEAT_COOL_MAP[command]})
		retry_count=0
		while (retry_count<NEST_MAX_RETRIES):
			self._cached=False
			self._send_command(send_data,self._shared_url)
			retry_count=retry_count+1
			if (NEST_HEAT_COOL_MAP[command]==self.get_heat_cool_mode()):
				return True
			time.sleep(NEST_RETRY_WAIT)
		return False

			
	def set_range_temps(self,low_temp,high_temp):
		"""Sets the high and low temperatures to be maintained by the Nest when in 'range' heat/cool mode.
	
				Arguments:
					low_temp - The lowest (coldest) temperature to allow before heating kicks in.
					high_temp - The highest (hottest) temperature allowed before cooling kicks in.
		"""
		self._refresh_status()
		send_data=json.dumps({NEST_RANGE_TEMP_LOW:self._apply_temp_scale_c(low_temp),
							NEST_RANGE_TEMP_HIGH:self._apply_temp_scale_c(high_temp)})
		retry_count=0
		while (retry_count<NEST_MAX_RETRIES):
			self._cached=False
			self._send_command(send_data,self._shared_url)
			retry_count=retry_count+1
			range_temps=self.get_range_temps()
			if (round(range_temps['low'])==round(low_temp) and round(range_temps['high'])==round(high_temp)):
				return True
			time.sleep(NEST_RETRY_WAIT)
		return False
	
	def set_target_temp(self,new_temp):
		"""Sets a new target temperature on the Nest. This is the same as turning physical Nest dial.
	
				Arguments:
					new_temp - The temperature the Nest will try to reach and maintain.
		"""
		self._refresh_status()
		send_data=json.dumps({NEST_TARGET_TEMP:self._apply_temp_scale_c(new_temp),NEST_TARGET_CHANGE_PENDING:True})
		retry_count=0
		while (retry_count<NEST_MAX_RETRIES or self.target_temp_change_is_pending()):
			self._cached=False
			self._send_command(send_data,self._shared_url)
			retry_count=retry_count+1
			if (round(new_temp)==round(self.get_target_temp())):
				return True
			time.sleep(NEST_RETRY_WAIT)
		return False
		
# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.

################################################################################
kHvacModeEnumToStrMap = {
	indigo.kHvacMode.Cool				: u"cool",
	indigo.kHvacMode.Heat				: u"heat",
	indigo.kHvacMode.HeatCool			: u"auto",
	indigo.kHvacMode.Off				: u"off",
	indigo.kHvacMode.ProgramHeat		: u"program heat",
	indigo.kHvacMode.ProgramCool		: u"program cool",
	indigo.kHvacMode.ProgramHeatCool	: u"program auto"
}

kFanModeEnumToStrMap = {
	indigo.kFanMode.AlwaysOn			: u"always on",
	indigo.kFanMode.Auto				: u"auto"
}

map_to_indigo_hvac_mode={'cool':indigo.kHvacMode.Cool,
						'heat':indigo.kHvacMode.Heat,
						'auto':indigo.kHvacMode.HeatCool,
						'range':indigo.kHvacMode.HeatCool,
						'off':indigo.kHvacMode.Off}
						
map_to_indigo_fan_mode={'on':indigo.kFanMode.AlwaysOn,
						'auto':indigo.kFanMode.Auto}

def _lookupActionStrFromHvacMode(hvacMode):
	return kHvacModeEnumToStrMap.get(hvacMode, u"unknown")

def _lookupActionStrFromFanMode(fanMode):
	return kFanModeEnumToStrMap.get(fanMode, u"unknown")

################################################################################
class Plugin(indigo.PluginBase):
	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.debug = False

	def __del__(self):
		indigo.PluginBase.__del__(self)

	########################################
	# Internal utility methods. Some of these are useful to provide
	# a higher-level abstraction for accessing/changing thermostat
	# properties or states.
	######################
	def _getTempSensorCount(self, dev):
		return int(dev.pluginProps["NumTemperatureInputs"])

	def _getHumiditySensorCount(self, dev):
		return int(dev.pluginProps["NumHumidityInputs"])

	######################
	def _changeTempSensorCount(self, dev, count):
		newProps = dev.pluginProps
		newProps["NumTemperatureInputs"] = count
		dev.replacePluginPropsOnServer(newProps)

	def _changeHumiditySensorCount(self, dev, count):
		newProps = dev.pluginProps
		newProps["NumHumidityInputs"] = count
		dev.replacePluginPropsOnServer(newProps)

	def _changeAllTempSensorCounts(self, count):
		for dev in indigo.devices.iter("self"):
			self._changeTempSensorCount(dev, count)

	def _changeAllHumiditySensorCounts(self, count):
		for dev in indigo.devices.iter("self"):
			self._changeHumiditySensorCount(dev, count)

	######################
	def _changeTempSensorValue(self, dev, index, value):
		# Update the temperature value at index. If index is greater than the "NumTemperatureInputs"
		# an error will be displayed in the Event Log "temperature index out-of-range"
		stateKey = u"temperatureInput" + str(index)
		dev.updateStateOnServer(stateKey, value)
		self.debugLog(u"\"%s\" called update %s %d" % (dev.name, stateKey, value))

	def _changeHumiditySensorValue(self, dev, index, value):
		# Update the humidity value at index. If index is greater than the "NumHumidityInputs"
		# an error will be displayed in the Event Log "humidity index out-of-range"
		stateKey = u"humidityInput" + str(index)
		dev.updateStateOnServer(stateKey, value)
		self.debugLog(u"\"%s\" called update %s %d" % (dev.name, stateKey, value))

	######################
	# Poll all of the states from the thermostat and pass new values to
	# Indigo Server.
	def _refreshStatesFromHardware(self, dev, logRefresh, commJustStarted):
		# As an example here we update the temperature and humidity
		# sensor states to random values.
		self._changeTempSensorValue(dev, 1, self._myNest.get_temp())
		self._changeHumiditySensorValue(dev, 1, self._myNest.get_humidity())

		#	Other states that should also be updated:
				
		dev.updateStateOnServer("hvacOperationMode", map_to_indigo_hvac_mode[self._myNest.get_heat_cool_mode()])
		dev.updateStateOnServer("hvacFanMode", map_to_indigo_fan_mode[self._myNest.get_fan_mode()])
		dev.updateStateOnServer("hvacCoolerIsOn", self._myNest.ac_is_on())
		dev.updateStateOnServer("hvacHeaterIsOn", self._myNest.heat_is_on())
		dev.updateStateOnServer("hvacFanIsOn", self._myNest.fan_is_on())
		dev.updateStateOnServer("away",self._myNest.away_is_active())
		if (self._myNest.get_heat_cool_mode()=="cool"):
			dev.updateStateOnServer("setpointCool", self._myNest.get_target_temp())
			dev.updateStateOnServer("setpointHeat", 0)
		elif (self._myNest.get_heat_cool_mode()=="heat"):
			dev.updateStateOnServer("setpointHeat", self._myNest.get_target_temp())
			dev.updateStateOnServer("setpointCool", 0)
		elif (self._myNest.get_heat_cool_mode()=="range"):
			range_temps=self._myNest.get_range_temps()
			dev.updateStateOnServer("setpointCool", range_temps['high'])
			dev.updateStateOnServer("setpointHeat", range_temps['low'])
		if logRefresh:
			indigo.server.log(u"received \"%s\" cool setpoint update to %.1f°" % (dev.name, dev.states["setpointCool"]))
			indigo.server.log(u"received \"%s\" heat setpoint update to %.1f°" % (dev.name, dev.states["setpointHeat"]))
			indigo.server.log(u"received \"%s\" main mode update to %s" % (dev.name, _lookupActionStrFromHvacMode(dev.states["hvacOperationMode"])))
			indigo.server.log(u"received \"%s\" fan mode update to %s" % (dev.name, _lookupActionStrFromFanMode(dev.states["hvacFanMode"])))
			indigo.server.log(u"received \"%s\" away status to %s" % (dev.name, dev.states["away"]))

	######################
	# Process action request from Indigo Server to change main thermostat's main mode.
	def _handleChangeHvacModeAction(self, dev, newHvacMode):
		# Command hardware module (dev) to change the thermostat mode here:
		
		sendSuccess=self._myNest.set_heat_cool_mode(_lookupActionStrFromHvacMode(newHvacMode))

		actionStr = _lookupActionStrFromHvacMode(newHvacMode)

		if sendSuccess:
			# If success then log that the command was successfully sent.
			indigo.server.log(u"sent \"%s\" mode change to %s" % (dev.name, actionStr))

			# And then tell the Indigo Server to update the state.
			dev.updateStateOnServer("hvacOperationMode", newHvacMode)
		else:
			# Else log failure but do NOT update state on Indigo Server.
			indigo.server.log(u"send \"%s\" mode change to %s failed" % (dev.name, actionStr), isError=True)

	######################
	# Process action request from Indigo Server to change thermostat's fan mode.
	def _handleChangeFanModeAction(self, dev, newFanMode):
		# Command hardware module (dev) to change the fan mode here:
		sendSuccess = self._myNest.set_fan_mode(_lookupActionStrFromFanMode(newFanMode))		# Set to False if it failed.
		actionStr = _lookupActionStrFromFanMode(newFanMode)
		if sendSuccess:
			# If success then log that the command was successfully sent.
			indigo.server.log(u"sent \"%s\" fan mode change to %s" % (dev.name, actionStr))

			# And then tell the Indigo Server to update the state.
			dev.updateStateOnServer("hvacFanMode", newFanMode)
		else:
			# Else log failure but do NOT update state on Indigo Server.
			indigo.server.log(u"send \"%s\" fan mode change to %s failed" % (dev.name, actionStr), isError=True)

	######################
	# Process action request from Indigo Server to change a cool/heat setpoint.
	def _handleChangeSetpointAction(self, dev, newSetpoint, logActionName, stateKey):
		if newSetpoint < 40.0:
			newSetpoint = 40.0		# Arbitrary -- set to whatever hardware minimum setpoint value is.
		elif newSetpoint > 95.0:
			newSetpoint = 95.0		# Arbitrary -- set to whatever hardware maximum setpoint value is.

		sendSuccess = False
		
		if stateKey == u"setpointCool":
			# Command hardware module (dev) to change the cool setpoint to newSetpoint here:
			if (self._myNest.get_heat_cool_mode()=="cool"):
				sendSuccess=self._myNest.set_target_temp(newSetpoint)
			elif (self._myNest.get_heat_cool_mode()=="heat"):
				sendSuccess=False
			elif (self._myNest.get_heat_cool_mode()=="range"):
				range_temps=self._myNest.get_range_temps()
				sendSuccess=self._myNest.set_range_temps(range_temps['low'],newSetpoint)
		elif stateKey == u"setpointHeat":
			# Command hardware module (dev) to change the heat setpoint to newSetpoint here:
			if (self._myNest.get_heat_cool_mode()=="cool"):
				sendSuccess=False
			elif (self._myNest.get_heat_cool_mode()=="heat"):
				sendSuccess=self._myNest.set_target_temp(newSetpoint)
			elif (self._myNest.get_heat_cool_mode()=="range"):
				range_temps=self._myNest.get_range_temps()
				sendSuccess=self._myNest.set_range_temps(newSetpoint,range_temps['high'])

		if sendSuccess:
			# If success then log that the command was successfully sent.
			indigo.server.log(u"sent \"%s\" %s to %.1f°" % (dev.name, logActionName, newSetpoint))

			# And then tell the Indigo Server to update the state.
			dev.updateStateOnServer(stateKey, newSetpoint)
		else:
			# Else log failure but do NOT update state on Indigo Server.
			indigo.server.log(u"send \"%s\" %s to %.1f° failed" % (dev.name, logActionName, newSetpoint), isError=True)

	########################################
	def startup(self):
		self.debugLog(u"startup called")

	def shutdown(self):
		self.debugLog(u"shutdown called")

	########################################
	def runConcurrentThread(self):
		try:
			while True:
				for dev in indigo.devices.iter("self"):
					if not dev.enabled:
						continue

					# Plugins that need to poll out the status from the thermostat
					# could do so here, then broadcast back the new values to the
					# Indigo Server.
					self._refreshStatesFromHardware(dev, False, False)

				self.sleep(3)
		except self.StopThread:
			pass	# Optionally catch the StopThread exception and do any needed cleanup.

	########################################
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		username=valuesDict["username"]
		password=valuesDict["password"]
		devicename=valuesDict["devicename"]
		devicelocation=valuesDict["devicelocation"]
		errorDict=indigo.Dict()

		try:
			testNest=NestThermostat(username,password,devicename,devicelocation)
		except:
			errorDict["username"]="Couldn't connect. Is your username correct?"
			errorDict["password"]="Couldn't connect. Is your password correct?"
			errorDict["devicename"]="Couldn't connect. Is your device name correct?"
			errorDict["devicelocation"]="Couldn't connect. Is your device location correct?"
			return (False,valuesDict,errorDict)

		return (True, valuesDict)

	########################################
	def deviceStartComm(self, dev):
		# Called when communication with the hardware should be established.
		# Here would be a good place to poll out the current states from the
		# thermostat. If periodic polling of the thermostat is needed (that
		# is, it doesn't broadcast changes back to the plugin somehow), then
		# consider adding that to runConcurrentThread() above.
		# XXX
		
		# Set the Equipment State UI to always True
		newProps = dev.pluginProps
		newProps["ShowCoolHeatEquipmentStateUI"]=True
		newProps["address"]=dev.pluginProps["devicelocation"]+" : "+dev.pluginProps["devicename"]
		newProps["NumTemperatureInputs"]=1
		newProps["NumHumidityInputs"]=1
		dev.replacePluginPropsOnServer(newProps)
		
		username=dev.pluginProps["username"]
		password=dev.pluginProps["password"]
		devicename=dev.pluginProps["devicename"]
		devicelocation=dev.pluginProps["devicelocation"]

		self._myNest=NestThermostat(username,password,devicename,devicelocation)
		self._refreshStatesFromHardware(dev, True, True)

	def deviceStopComm(self, dev):
		# Called when communication with the hardware should be shutdown.
		pass

	########################################
	# Thermostat Action callback
	######################
	# Main thermostat action bottleneck called by Indigo Server.
	def actionControlThermostat(self, action, dev):
		###### SET HVAC MODE ######
		if action.thermostatAction == indigo.kThermostatAction.SetHvacMode:
			self._handleChangeHvacModeAction(dev, action.actionMode)

		###### SET FAN MODE ######
		elif action.thermostatAction == indigo.kThermostatAction.SetFanMode:
			self._handleChangeFanModeAction(dev, action.actionMode)

		###### SET COOL SETPOINT ######
		elif action.thermostatAction == indigo.kThermostatAction.SetCoolSetpoint:
			newSetpoint = action.actionValue
			self._handleChangeSetpointAction(dev, newSetpoint, u"change cool setpoint", u"setpointCool")

		###### SET HEAT SETPOINT ######
		elif action.thermostatAction == indigo.kThermostatAction.SetHeatSetpoint:
			newSetpoint = action.actionValue
			self._handleChangeSetpointAction(dev, newSetpoint, u"change heat setpoint", u"setpointHeat")

		###### DECREASE/INCREASE COOL SETPOINT ######
		elif action.thermostatAction == indigo.kThermostatAction.DecreaseCoolSetpoint:
			newSetpoint = dev.coolSetpoint - action.actionValue
			self._handleChangeSetpointAction(dev, newSetpoint, u"decrease cool setpoint", u"setpointCool")

		elif action.thermostatAction == indigo.kThermostatAction.IncreaseCoolSetpoint:
			newSetpoint = dev.coolSetpoint + action.actionValue
			self._handleChangeSetpointAction(dev, newSetpoint, u"increase cool setpoint", u"setpointCool")

		###### DECREASE/INCREASE HEAT SETPOINT ######
		elif action.thermostatAction == indigo.kThermostatAction.DecreaseHeatSetpoint:
			newSetpoint = dev.heatSetpoint - action.actionValue
			self._handleChangeSetpointAction(dev, newSetpoint, u"decrease heat setpoint", u"setpointHeat")

		elif action.thermostatAction == indigo.kThermostatAction.IncreaseHeatSetpoint:
			newSetpoint = dev.heatSetpoint + action.actionValue
			self._handleChangeSetpointAction(dev, newSetpoint, u"increase heat setpoint", u"setpointHeat")

		###### REQUEST STATE UPDATES ######
		elif action.thermostatAction in [indigo.kThermostatAction.RequestStatusAll, indigo.kThermostatAction.RequestMode,
		indigo.kThermostatAction.RequestEquipmentState, indigo.kThermostatAction.RequestTemperatures, indigo.kThermostatAction.RequestHumidities,
		indigo.kThermostatAction.RequestDeadbands, indigo.kThermostatAction.RequestSetpoints]:
			self._refreshStatesFromHardware(dev, True, False)

	########################################
	# Custom Plugin Action callbacks (defined in Actions.xml)
	######################
	def setAwayStatus(self, pluginAction, dev):
		awayStatus = pluginAction.props.get(u"away")
		sendSuccess=self._myNest.set_away_state(awayStatus)

		if sendSuccess:
			# If success then log that the command was successfully sent.
			indigo.server.log(u"sent \"%s\" %s to %d" % (dev.name, "set away status", awayStatus))

			# And then tell the Indigo Server to update the state:
			dev.updateStateOnServer("away", awayStatus)
		else:
			# Else log failure but do NOT update state on Indigo Server.
			indigo.server.log(u"send \"%s\" %s to %d failed" % (dev.name, "set away status", awayStatus), isError=True)

