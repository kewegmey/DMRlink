#!/usr/bin/env python
#
###############################################################################
#   Copyright (C) 2023 Kory Wegmeyer, kory@wegmeyer.io
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software Foundation,
#   Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA
###############################################################################
#


from __future__ import print_function

from twisted.internet.protocol import Factory, Protocol
from twisted.protocols.basic import NetstringReceiver
from twisted.internet import reactor
from twisted.internet import task

from binascii import b2a_hex as ahex
from time import time
from importlib import import_module

import cPickle as pickle

from dmr_utils.utils import hex_str_3, hex_str_4, int_id

from dmrlink import IPSC, mk_ipsc_systems, systems, reportFactory, REPORT_OPCODES, build_aliases
from ipsc.ipsc_const import BURST_DATA_TYPE


__author__      = 'Kory Wegmeyer'
__copyright__   = 'Copyright (C) 2023 Kory Wegmeyer, kory@wegmeyer.io'
__credits__     = 'Adam Fast, KC0YLK; Dave Kierzkowski, KD8EYF; Steve Zingman, N4IRS; Mike Zingman, N4IRR; Cortney T. Buffington, N0MJS'
__license__     = 'GNU GPLv3'
__maintainer__  = 'Kory Wegmeyer'
__email__       = 'kory@wegmeyer.io'


# Minimum time between different subscribers transmitting on the same TGID
#
TS_CLEAR_TIME = .2

# Declare this here so that we can define functions around it
#
BRIDGES = {}

# Timed loop used for reporting IPSC status
#
# REPORT BASED ON THE TYPE SELECTED IN THE MAIN CONFIG FILE
def config_reports(_config, _logger, _factory):
    if _config['REPORTS']['REPORT_NETWORKS'] == 'PRINT':
        def reporting_loop(_logger):
            _logger.debug('Periodic Reporting Loop Started (PRINT)')
            for system in _config['SYSTEMS']:
                print_master(_config, system)
                print_peer_list(_config, system)
        
        reporting = task.LoopingCall(reporting_loop, _logger)
        reporting.start(_config['REPORTS']['REPORT_INTERVAL'])
        report_server = False
                
    elif _config['REPORTS']['REPORT_NETWORKS'] == 'NETWORK':
        def reporting_loop(_logger, _server):
            _logger.debug('Periodic Reporting Loop Started (NETWORK)')
            _server.send_config()
            _server.send_bridge()
            
        _logger.info('DMRlink TCP reporting server starting')
        
        report_server = _factory(_config, _logger)
        report_server.clients = []
        reactor.listenTCP(_config['REPORTS']['REPORT_PORT'], report_server)
        
        reporting = task.LoopingCall(reporting_loop, _logger, report_server)
        reporting.start(_config['REPORTS']['REPORT_INTERVAL'])

    else:
        def reporting_loop(_logger):
            _logger.debug('Periodic Reporting Loop Started (NULL)')
        report_server = False
    
    return report_server

    
class confbridgeIPSC(IPSC):
    def __init__(self, _name, _config, _logger, _report):
        IPSC.__init__(self, _name, _config, _logger, _report)

        self.STATUS = {
            1: {'RX_TGID':'\x00', 'TX_TGID':'\x00', 'RX_TIME':0, 'TX_TIME':0, 'RX_SRC_SUB':'\x00', 'TX_SRC_SUB':'\x00'},
            2: {'RX_TGID':'\x00', 'TX_TGID':'\x00', 'RX_TIME':0, 'TX_TIME':0, 'RX_SRC_SUB':'\x00', 'TX_SRC_SUB':'\x00'}
        }
        
        self.last_seq_id = '\x00'
        self.call_start = 0

class confbridgeReportFactory(reportFactory):
        
    def send_bridge(self):
        serialized = pickle.dumps(BRIDGES, protocol=pickle.HIGHEST_PROTOCOL)
        self.send_clients(REPORT_OPCODES['BRIDGE_SND']+serialized)
        
    def send_bridgeEvent(self, _data):
        self.send_clients(REPORT_OPCODES['BRDG_EVENT']+_data)
        
    
if __name__ == '__main__':
    import argparse
    import sys
    import os
    import signal
    
    from ipsc.dmrlink_config import build_config
    from ipsc.dmrlink_log import config_logging
    
    # Change the current directory to the location of the application
    os.chdir(os.path.dirname(os.path.realpath(sys.argv[0])))

    # CLI argument parser - handles picking up the config file from the command line, and sending a "help" message
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', action='store', dest='CFG_FILE', help='/full/path/to/config.file (usually dmrlink.cfg)')
    parser.add_argument('-ll', '--log_level', action='store', dest='LOG_LEVEL', help='Override config file logging level.')
    parser.add_argument('-lh', '--log_handle', action='store', dest='LOG_HANDLERS', help='Override config file logging handler.')
    cli_args = parser.parse_args()

    if not cli_args.CFG_FILE:
        cli_args.CFG_FILE = os.path.dirname(os.path.abspath(__file__))+'/dmrlink.cfg'
    
    # Call the external routine to build the configuration dictionary
    CONFIG = build_config(cli_args.CFG_FILE)
    
    # Call the external routing to start the system logger
    if cli_args.LOG_LEVEL:
        CONFIG['LOGGER']['LOG_LEVEL'] = cli_args.LOG_LEVEL
    if cli_args.LOG_HANDLERS:
        CONFIG['LOGGER']['LOG_HANDLERS'] = cli_args.LOG_HANDLERS
    logger = config_logging(CONFIG['LOGGER'])
    logger.info('DMRlink \'dmrlink.py\' (c) 2013 - 2015 N0MJS & the K0USY Group - SYSTEM STARTING...')
    
    # Set signal handers so that we can gracefully exit if need be
    def sig_handler(_signal, _frame):
        logger.info('*** DMRLINK IS TERMINATING WITH SIGNAL %s ***', str(_signal))
        for system in systems:
            systems[system].de_register_self()
        reactor.stop()
    
    for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGQUIT]:
        signal.signal(sig, sig_handler)
    
    # INITIALIZE THE REPORTING LOOP
    report_server = config_reports(CONFIG, logger, confbridgeReportFactory)
        
    # INITIALIZE AN IPSC OBJECT (SELF SUSTAINING) FOR EACH CONFIGURED IPSC
    systems = mk_ipsc_systems(CONFIG, logger, systems, confbridgeIPSC, report_server)

    
    # INITIALIZATION COMPLETE -- START THE REACTOR
    reactor.run()
