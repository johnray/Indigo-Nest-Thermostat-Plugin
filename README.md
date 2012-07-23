Nest Thermostat Indigo Pro Plugin
=================================

This plugin implements all the major features of an Indigo thermostat, including activating the "Away" state of the Nest thermostat. It supports multiple thermostats, although they will each need to be added as separate instances within Indigo.

> The core of this plugin is based on the NestThermostat Python class, also available from github (http://github.com/johnray).

Installation
-------------
To install the Nest plugin, follow these instructions:

1. Download and unzip the plugin on the same computer running Indigo 5.x Pro. 
2. The plugin will unzip to a folder structure named "Nest Thermostat.indigoPlugin" - double-click this file.
3. When prompted, choose to Install and Enable the plugin.
4. Now you just need to add a Nest thermostat device to your device list.

Adding and Configuring a Nest Device
-------------------------------------
To add an instance of a Nest thermostat to Indigo, complete these steps:

1. Within the Indigo device listing window, click the "New" button in the toolbar.
2. Provide a Name and Description for the device.
3. Set the Type to "Pro Plugin".
4. From the Plugin menu that appears, choose the "Nest Thermostat" option.
5. From the Model menu, choose "Nest Thermostat Module".
6. A configuration dialog for the Nest is shown.  Enter your Nest.com Login and Password.
7. Enter the Name and Location of the Nest you want to control. These must match the name and location you created on Nest.com.
8. Click Save.  If there are any errors, you must correct them before proceeding.
9. The Nest instance is added and is available in your device list.

Tips for working with the Nest Plugin
-------------------------------------
- Temperatures are automatically converted between Fahrenheit and Celsius depending on your Nest settings. In other words, just use the Nest and don't worry about temperature conversions.
- When in cooling mode, the cool setpoint sets the target Nest temperature. In heating mode, the heat setpoint sets the target temperature. 
- When the nest is set to maintain a range, the cool setpoint (high temp) determines when cooling will kick in and the heat setpoint (low temp) when heating will kick in.
- It may take a second or two for controls to update the Nest. The Nest.com website handles controlling your device - this plugin provides an interface to the website, not your physical hardware. Short story - controls are fast, but not instantaneous.
- Supported modes are Heat, Cool, Range (maintain a range of temperatures), and Off.  The Indigo "Program Cool", "Program Heat", etc. modes are listed when creating triggers/actions (I don't think I can disable that) but are not used for anything. The Nest program will always be running, but any settings you make through this plugin will be the same as if you made them on the Nest.com website or on the Nest device itself.
- The Away state is supported by the plugin. To active/deactivate the Away state, you'll need to define an Action that uses the "Pro Plugin" Type. Select the "Nest Thermostat" plugin and the "Set Away Status" Action.
