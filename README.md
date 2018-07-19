# A/V NodeServer for PolyGlot V2

This is a generic A/V device node server for the [Universal Devices ISY994i](https://www.universal-devices.com/residential/ISY) [Polyglot interface](http://www.universal-devices.com/developers/polyglot/docs/) with  [Polyglot V2](https://github.com/Einstein42/udi-polyglotv2)

(c) Brad Whitted
MIT License

## How it works

### User perspective:
This nodeserver supports multiple A/V devices, but only if they have been built into the code.  The supported devices
are listed below along with any required parameters needed to specify how to connect to them.  Each one is particular
to that device and will have different requirements.
   
### Developer perspective:
This nodeserver is built on a state machine framework using the transitions python3 library.  Adding support for
new devices is fairly easy.  To add support for a new device:

  1. Subclass AVDevice and override the indicated methods to implement the device client communication layer.
     The state machine will drive the calls to these methods when necessary.
  2. Subclass the AVNode class, which is a superclass of the PolyGlot V2 Node.  The AVDevice class defines
     a Listener class that can be inherited by the new class to listen for events from the device client communication
     instances.
  3. Add config parameter parsing and/or SSDP parsing to NodeFactory.get_params().
  4. Update NodeFactory.on_ssdp_response() to build the new node.
  5. Update the node definitions, nls entries and editors as needed.
 
The included Pioneer VSX-1021 and Sony Bravia devices are available as examples

### Supported Devices:
  1. Pioneer VSX-1021 (possibly other VSX series, but use the VSX1021 custom parameter to define them) receiver
  
     Custom config parameters:
     
       * VSX1021xxxx = Host IP and port of receiver, i.e. 192.168.1.52:23
       
  2. Sony Bravia XBR-65X810C (possibly other Bravia series) TV

SSDP will search the network for your devices (the devices should be on.  If they are off, then they might be missed).
If SSDP doesn't find your devices, then you can define custom parameters for it as indicated.  If defining custom
parameters, then you'll need to restart the nodeserver after they are defined.

### Installation
1. Backup Your ISY in case of problems!  **Really, do the backup, please**
2. Go to the Polyglot Store in the UI and install A/VServer.
3. Add A/VServer NodeServer in Polyglot
4. Open Admin Console (if you already had it open, then close and re-open)
5. You should now have a node called AV Controller
6. Add appropriate custom parameters for your device if the SSDP searach didn't find them (see How it works above)
7. Restart the nodeserver if you added custom parameters

If you add more A/V devices after initial install/setup, just turn them on and then click the 'Discover' button on the
controller page to force an SSDP search.  If you have to add custom parameters, then a restart of the nodeserver
will be required.

### Requirements
1. [Polyglot V2](https://github.com/UniversalDevicesInc/polyglot-v2) >= 2.2.0
2. This has only been tested with ISY 5.0.12 so it is not confirmed to work with any prior version.

### Known Issues
- [ ] The device status doesn't update when the nodeserver stops.  This is because the PolyGlot Interface disconnects
      the MQTT connection prior to calling the nodes stop method which breaks the ability of a node to update any
      ISY related information when it is being stopped.  PolyGlot does know how to modify the controller status and does
      so automatically.
