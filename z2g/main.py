#!/usr/bin/env python

import logging
import multiprocessing
import signal
import time
import yaml
import z2g.config
import z2g.log
import z2g.zabbix

from functools import partial
from concurrent.futures import ThreadPoolExecutor

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
    cfg.StrOpt('num_workers',
               default='10',
               help='Number of worker threads to deal with the connections to Zabbix API.'),
    cfg.StrOpt('seconds_to_sleep',
               default='30',
               help='Seconds to sleep between iterations.'),
]

CONF = cfg.CONF

def stop(signum, frame):
    stop_event.set()

def parse_metrics():
    stream = open(CONF.metrics_file, 'r')
    return yaml.load(stream)

def get_host_metrics(host, zutils_obj=z2g.zabbix.ZabbixUtils(), d_metrics={}):
    return zutils_obj.get_items_by_host(host, filters=d_metrics[host])

def main():
    try:
        z2g.config.parse_args(sys.argv, default_config_files=["/etc/z2g.conf"])
    except cfg.ConfigFilesNotFoundError:
        cfgfile = CONF.config_file[-1] if CONF.config_file else None
        print "Could not find configuration file %s." % cfgfile
        sys.exit(-1)
    z2g.log.setup_logging()

    zutils = z2g.zabbix.ZabbixUtils()
    hosts_per_hostgroup = zutils.get_hosts_per_hostgroup() 
    metrics = parse_metrics()

    d = {}
    for entity in metrics.keys():
        if entity == "hostgroups":
            for name, content in metrics[entity].iteritems():
                logger.debug("Analyzing hostgroup '%s': %s" % (name, content))
                d.update(dict(map(lambda x: [x,content["metrics"]], hosts_per_hostgroup[content["zabbix_id"]])))
        elif entity == "hosts":
            for name, content in metrics[entity].iteritems():
                d.update(dict([(content["zabbix_id"], content["metrics"])]))

if __name__ == '__main__':
    stop_event = multiprocessing.Event()
    signal.signal(signal.SIGTERM, stop)

    while not stop_event.is_set():
        with ThreadPoolExecutor(max_workers=CONF.num_workers) as executor:
            before = time.time()
            mapfunc = partial(get_host_metrics, zutils_obj=zutils, d_metrics=d)
            for metrics in executor.map(mapfunc, d.keys()):
                for k,v in metrics:
                    send_to_statsd(k, v, remove_domain="ifca.es")
            after = time.time()

        logging.info("Gathering Zabbix metrics for %s hosts took %s seconds." % (len(d.keys()), after-before))
        time.sleep(CONF.seconds_to_sleep)
