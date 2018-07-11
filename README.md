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
  2. Subclass the PolyAVDevice class, which is a superclass of the PolyGlot V2 Node.  The AVDevice class defines
     a Listener class that can be inherited by the new class to listen for events from the device client communication
     instances.
  3. Add config parameter parsing and custom data implementations into the AVController class.  If all you need is
     name, host and port, no changes should be necessary as long as the custom parameter parsing is not changed.
  4. Update the node_factory to build the new node.
  5. Update the node definitions, nls entries and editors as needed.
 
The included Pioneer VSX-1021 and Sony Bravia devices are available as examples

### Supported Devices:
  1. Pioneer VSX-1021 (possibly other VSX series) receiver
  
     Required custom config parameters:
     
       * VSX1021_x_NAME = Whatever name you want the node called
       * VSX1021_x_HOST = Host IP of the receiver
       * VSX1021_X_PORT = Port to connect to on the receiver
       
     x = a number from 0 - 9 (Only 10 devices supported)
       
  2. Sony Bravia XBR-65X810C (possibly other Bravia series) TV

Once the config parameters are defined, restart the nodeserver and the new nodes will be created in ISY and the
connection to the device will be created.

### Installation
1. Backup Your ISY in case of problems!  **Really, do the backup, please**
2. Go to the Polyglot Store in the UI and install A/VServer.
3. Add A/VServer NodeServer in Polyglot
4. Open Admin Console (if you already had it open, then close and re-open)
5. You should now have a node called AV Controller
6. Add appropriate keys for your device (see How it works above)
7. Restart the nodeserver

### Requirements
1. [Polyglot V2](https://github.com/UniversalDevicesInc/polyglot-v2) >= 2.2.0
2. This has only been tested with ISY 5.0.12 so it is not confirmed to work with any prior version.

### Known Issues
- [ ] The device status doesn't update when the nodeserver stops.  This is because the PolyGlot Interface disconnects
      the MQTT connection prior to calling the nodes stop method which breaks the ability of a node to update any
      ISY related information when it is being stopped.  PolyGlot does know how to modify the controller status and does
      so automatically.
