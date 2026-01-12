"""
Functions for communicating with GDA
"""

import stomp
import json
import sys

from .env_functions import get_beamline


CONTROL_NAME = "{beamline}-control"

def gda_datavis_file_message(filepath: str, connect_to: str | None = None):
    """
    Send an ActiveMQ message using stomp with a filepath.
    This will be picked up by any GDA instance connected to the control machine in the DataVis perspective.

    :param filepath: path to file to send, e.g. "/dls/i16/data/2022/cm31138-14/processed/960677_msmapper.nxs"
    :param connect_to: name of beamline control machine
    """
    if connect_to is None:
        beamline = get_beamline(filename=filepath)
        connect_to = CONTROL_NAME.format(beamline=beamline)

    conn = stomp.Connection([(connect_to, 61613)], auto_content_length=False)

    try:
        # conn.start()
        conn.connect()
        print(f"Connected to {connect_to}")

        message = json.dumps({'filePath': filepath})
        destination = '/topic/org.dawnsci.file.topic'
        conn.send(destination, message, ack='auto')
        print('Message sent!')
        conn.disconnect()
    except Exception as err:
        print(err)
        print('Message failed to send.')

