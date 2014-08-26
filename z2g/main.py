#!/usr/bin/env python

import logging
import multiprocessing
import signal
import sys
import time
import yaml
import z2g.config
import z2g.graphite
import z2g.log
import z2g.zabbix

from concurrent.futures import ThreadPoolExecutor
from functools import partial
from oslo.config import cfg

logger = logging.getLogger('pyzabbix')
logger.setLevel(logging.INFO)
logger = logging.getLogger('requests.packages.urllib3.connectionpool')
logger.setLevel(logging.INFO)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

opts = [
    cfg.StrOpt('metrics_file',
               default='/etc/z2g/metrics.conf',
               help='Metrics configuration file.'),
    cfg.IntOpt('num_workers',
               default='10',
               help='Number of worker threads to deal with the connections to Zabbix API.'),
    cfg.IntOpt('seconds_to_sleep',
               default='30',
               help='Seconds to sleep between iterations.'),
]

CONF = cfg.CONF
CONF.register_opts(opts)

class Z2G(object):
    def __init__(self):
        self.zutils = z2g.zabbix.ZabbixUtils()

    def parse_metrics(self):
        f = open(CONF.metrics_file, 'r')
        metrics = yaml.load(f)
        hosts_per_hostgroup = self.zutils.get_hosts_per_hostgroup() 
        
        d = {}
        for entity in metrics.keys():
            if entity == "hostgroups":
                for name, content in metrics[entity].iteritems():
                    logger.debug("Analyzing hostgroup '%s': %s" % (name, content))
                    d.update(dict(map(lambda x: [x,content["metrics"]], hosts_per_hostgroup[content["zabbix_id"]])))
            elif entity == "hosts":
                for name, content in metrics[entity].iteritems():
                    d.update(dict([(content["zabbix_id"], content["metrics"])]))
        return d


    # FIXME: host must match the name in Zabbix
    def get_host_metrics(self, host, d_metrics={}):
        return self.zutils.get_items_by_host(host, filters=d_metrics[host])


def stop(signum, frame):
    stop_event.set()

def work():
    z2g_obj = Z2G()
    d_metrics = z2g_obj.parse_metrics()
    stop_event = multiprocessing.Event()
    #signal.signal(signal.SIGTERM, stop)

    while not stop_event.is_set():
        try:
            mapfunc = partial(z2g_obj.get_host_metrics, d_metrics=d_metrics)
            with ThreadPoolExecutor(max_workers=CONF.num_workers) as executor:
                before = time.time()
                for r in executor.map(mapfunc, d_metrics.keys()):
                    for k,v in r:
                        #z2g.graphite.send_to_stdout(k, v, domain="ifca.es")
                        z2g.graphite.send_to_statsd(k, v, domain="ifca.es")
                after = time.time()
                logging.info("Gathering&printing Zabbix metrics for %s hosts took %s seconds." % (len(d_metrics.keys()), after-before))
            time.sleep(CONF.seconds_to_sleep)
        except KeyboardInterrupt:
            logging.info("Exiting on user request") 
            stop_event.set()
