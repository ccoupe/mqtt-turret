#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import sys, traceback
import json
from datetime import datetime
from threading import Thread
import time

import time

class Homie_MQTT:

  def __init__(self, settings, ctlCb):
    self.settings = settings
    self.log = settings.log
    self.ctlCb = ctlCb
    # init server connection
    self.client = mqtt.Client(settings.mqtt_client_name, False)
    #self.client.max_queued_messages_set(3)
    hdevice = self.hdevice = self.settings.homie_device  # "device_name"
    hlname = self.hlname = self.settings.homie_name     # "Display Name"
    # beware async timing with on_connect
    #self.client.loop_start()
    #self.client.on_connect = self.on_connect
    #self.client.on_subscribe = self.on_subscribe
    self.client.on_message = self.on_message
    self.client.on_disconnect = self.on_disconnect
    rc = self.client.connect(settings.mqtt_server, settings.mqtt_port)
    if rc != mqtt.MQTT_ERR_SUCCESS:
        self.log.warn("network missing?")
        exit()
    self.client.loop_start()
      
    # short cuts to stuff we really care about
    self.hcmd_sub = "homie/"+hdevice+"/turret_1/control/set"
    self.hcmd_pub = "homie/"+hdevice+"/turret_1/control"
    self.hpan_pub = "homie/"+hdevice+"/turret_1/pan"
    self.htilt_pub = "homie/"+hdevice+"/turret_1/tilt"
    self.hpower_pub = "homie/"+hdevice+"/turret_1/power"
    
    self.log.debug("Homie_MQTT __init__")
    self.create_topics(hdevice, hlname)
    for sub in [self.hcmd_sub]:  
      rc,_ = self.client.subscribe(sub)
      if rc != mqtt.MQTT_ERR_SUCCESS:
        self.log.warn("Subscribe failed: %d" %rc)
      else:
        self.log.debug("Init() Subscribed to %s" % sub)
      
     
  def create_topics(self, hdevice, hlname):
    self.log.debug("Begin topic creation")
    # create topic structure at server - these are retained! 
    #self.client.publish("homie/"+hdevice+"/$homie", "3.0.1", mqos, retain=True)
    self.publish_structure("homie/"+hdevice+"/$homie", "3.0.1")
    self.publish_structure("homie/"+hdevice+"/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/$status", "ready")
    self.publish_structure("homie/"+hdevice+"/$mac", self.settings.macAddr)
    self.publish_structure("homie/"+hdevice+"/$localip", self.settings.our_IP)
    # could have three nodes: turrent, [ranger and display]
    self.publish_structure("homie/"+hdevice+"/$nodes", "turret_1")
    
    # turret_1 node
    self.publish_structure("homie/"+hdevice+"/turret_1/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/turret_1/$type", "audiosink")
    self.publish_structure("homie/"+hdevice+"/turret_1/$properties","pan,tilt,power,control")
    # control Property of 'turret_1'
    self.publish_structure("homie/"+hdevice+"/turret_1/control/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/turret_1/control/$datatype", "string")
    self.publish_structure("homie/"+hdevice+"/turret_1/control/$settable", "false")
    self.publish_structure("homie/"+hdevice+"/turret_1/control/$retained", "true")
    # pan Property of 'turret_1'
    self.publish_structure("homie/"+hdevice+"/turret_1/pan/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/turret_1/pan/$datatype", "integer")
    self.publish_structure("homie/"+hdevice+"/turret_1/pan/$format", "0:180")
    self.publish_structure("homie/"+hdevice+"/turret_1/pan/$settable", "false")
    self.publish_structure("homie/"+hdevice+"/turret_1/pan/$retained", "true")
    # tilt Property of 'turret_1'
    self.publish_structure("homie/"+hdevice+"/turret_1/tilt/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/turret_1/tilt/$datatype", "integer")
    self.publish_structure("homie/"+hdevice+"/turret_1/tilt/$format", "0:180")
    self.publish_structure("homie/"+hdevice+"/turret_1/tilt/$settable", "false")
    self.publish_structure("homie/"+hdevice+"/turret_1/tilt/$retained", "true")
    # power Property of 'turret_1'
    self.publish_structure("homie/"+hdevice+"/turret_1/power/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/turret_1/power/$datatype", "integer")
    self.publish_structure("homie/"+hdevice+"/turret_1/power/$format", "0:100")
    self.publish_structure("homie/"+hdevice+"/turret_1/power/$settable", "false")
    self.publish_structure("homie/"+hdevice+"/turret_1/power/$retained", "true")

   # Done with structure. 

    self.log.debug("homie topics created")
    # nothing else to publish 
    
  def publish_structure(self, topic, payload):
    self.client.publish(topic, payload, qos=1, retain=True)
    
  def on_subscribe(self, client, userdata, mid, granted_qos):
    self.log.debug("Subscribed to %s" % self.hurl_sub)

  def on_message(self, client, userdata, message):
    settings = self.settings
    topic = message.topic
    payload = str(message.payload.decode("utf-8"))
    #self.log.debug("on_message %s %s" % (topic, payload))
    try:
      if (topic == self.hcmd_sub):
        ctl_thr = Thread(target=self.ctlCb, args=(1, payload))
        ctl_thr.start()
      else:
        self.log.debug(f"on_message() unknown: {topic} {payload}")
    except:
      traceback.print_exc()

    
  def isConnected(self):
    return self.mqtt_connected

  def on_connect(self, client, userdata, flags, rc):
    self.log.debug("Subscribing: %s %d" (type(rc), rc))
    if rc == 0:
      self.log.debug("Connecting to %s" % self.mqtt_server_ip)
      rc,_ = self.client.subscribe(self.hurl_sub)
      if rc != mqtt.MQTT_ERR_SUCCESS:
        self.log.debug("Subscribe failed: ", rc)
      else:
        self.log.debug("Subscribed to %s" % self.hurl_sub)
        self.mqtt_connected = True
    else:
      self.log.debug("Failed to connect: %d" %rc)
    self.log.debug("leaving on_connect")
       
  def on_disconnect(self, client, userdata, rc):
    self.mqtt_connected = False
    log("mqtt reconnecting")
    self.client.reconnect()
      
    self.hpower_pub = "homie/"+hdevice+"/turret_1/power"
  def update_pan(self, angle):
    self.client.publish(self.hpan_pub, ang)
    
  def update_tilt(self, angle):
    self.client.publish(self.htilt_pub, ang)

  def update_angles(self, pan, tilt):
    self.client.publish(self.hpan_pub, pan)
    self.client.publish(self.htilt_pub, tilt)

  def update_power(self, power):
    self.client.publish(self.hpower_pub, power)
    
  def update_status(self, sts):
    self.client.publish(self.hcmd_pub, sts)
