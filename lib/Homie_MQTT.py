#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import sys, traceback
import json
from datetime import datetime
from threading import Thread
import time

import time

# Deal with multiple turrets but we only have ONE mqtt instance.
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
    ntur = len(settings.turrets)
    self.create_top(hdevice, hlname, ntur)
    
    self.hcmds_sub = []
    self.hcmds_pub = []
    self.hpans_pub = []
    self.htilts_pub = []
    self.hpowers_pub = []
    # short cuts to stuff we really care about
    for i in range(0, ntur):
      self.hcmds_sub.append(f"homie/{hdevice}/turret_{i+1}/control/set")
      self.hcmds_pub.append(f"homie/{hdevice}/turret_{i+1}/control")
      self.hpans_pub.append(f"homie/{hdevice}/turret_{i+1}/pan")
      self.htilts_pub.append(f"homie/{hdevice}/turret_{i+1}/tilt")
      self.hpowers_pub.append(f"homie/{hdevice}/turret_{i+1}/power")
      self.create_topics(hdevice, hlname, i+1)
      
    self.log.debug("Homie_MQTT __init__")
   
    for sub in self.hcmds_sub:  
      rc,_ = self.client.subscribe(sub)
      if rc != mqtt.MQTT_ERR_SUCCESS:
        self.log.warn("Subscribe failed: %d" %rc)
      else:
        self.log.debug("Init() Subscribed to %s" % sub)
      
  def create_top(self, hdevice, hlname, ntur):
    self.log.debug("Begin topic creation")
    # create topic structure at server - these are retained! 
    #self.client.publish("homie/"+hdevice+"/$homie", "3.0.1", mqos, retain=True)
    self.publish_structure("homie/"+hdevice+"/$homie", "3.0.1")
    self.publish_structure("homie/"+hdevice+"/$name", hlname)
    self.publish_structure("homie/"+hdevice+"/$status", "ready")
    self.publish_structure("homie/"+hdevice+"/$mac", self.settings.macAddr)
    self.publish_structure("homie/"+hdevice+"/$localip", self.settings.our_IP)
    # could have three nodes: turrent, [ranger and display]
    py = 'turret_1'
    for i in range(1, ntur):
      py += f',turret_{i+1}'
    self.publish_structure("homie/"+hdevice+"/$nodes", py)
    
    
  def create_topics(self, hdevice, hlname, tur):
    # turret_n node
    prefix = f"homie/{hdevice}/turret_{tur}"
    self.publish_structure(f"{prefix}/$name", hlname)
    self.publish_structure(f"{prefix}/$type", "rurret")
    self.publish_structure(f"{prefix}/$properties","pan,tilt,power,control")
    # control Property of 'turret_n'
    self.publish_structure(f"{prefix}/control/$name", hlname)
    self.publish_structure(f"{prefix}/control/$datatype", "string")
    self.publish_structure(f"{prefix}/control/$settable", "false")
    self.publish_structure(f"{prefix}/control/$retained", "true")
    # pan Property of 'turret_n'
    self.publish_structure(f"{prefix}/pan/$name", hlname)
    self.publish_structure(f"{prefix}/pan/$datatype", "integer")
    self.publish_structure(f"{prefix}/pan/$format", "0:180")
    self.publish_structure(f"{prefix}/pan/$settable", "false")
    self.publish_structure(f"{prefix}/pan/$retained", "true")
    # tilt Property of 'turret_n'
    self.publish_structure(f"{prefix}/tilt/$name", hlname)
    self.publish_structure(f"{prefix}/tilt/$datatype", "integer")
    self.publish_structure(f"{prefix}/tilt/$format", "0:180")
    self.publish_structure(f"{prefix}/tilt/$settable", "false")
    self.publish_structure(f"{prefix}/tilt/$retained", "true")
    # power Property of 'turret_n'
    self.publish_structure(f"{prefix}/power/$name", hlname)
    self.publish_structure(f"{prefix}/power/$datatype", "integer")
    self.publish_structure(f"{prefix}/power/$format", "0:100")
    self.publish_structure(f"{prefix}/power/$settable", "false")
    self.publish_structure(f"{prefix}/power/$retained", "true")

   # Done with structure. 

    self.log.debug(f"{prefix} topics created")
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
      for i in range(0, len(self.settings.turrets)):
        if topic == self.hcmds_sub[i]:
          ctl_thr = Thread(target=self.ctlCb, args=(i, payload))
          ctl_thr.start()
          break
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
  def update_pan(self, idx, angle):
    self.client.publish(self.hpans_pub[idx], ang)
    
  def update_tilt(self, idx, angle):
    self.client.publish(self.htilts_pub[idx], ang)

  def update_angles(self, idx, pan, tilt):
    self.client.publish(self.hpans_pub[idx], pan)
    self.client.publish(self.htilts_pub[idx], tilt)

  def update_power(self, idx, power):
    self.client.publish(self.hpower_pubs[idx], power)
    
  def update_status(self, idx, sts):
    self.client.publish(self.hcmds_pub[idx], sts)
