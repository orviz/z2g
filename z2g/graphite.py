import logging
import statsd
import time

from oslo.config import cfg

logger = logging.getLogger(__name__)

opts = [
    cfg.StrOpt('carbon_server',
               default='127.0.0.1',
               help='IP or hostname of the carbon server.'),
    cfg.StrOpt('carbon_port',
               default='2003',
               help='Port where carbon server is accesible.'),
    cfg.StrOpt('prefix',
               default='',
               help='Prefix used in the metrics.'),
]

CONF = cfg.CONF
CONF.register_opts(opts, group="graphite")


def remove_domain(message, domain):
    if domain:
        logger.debug("Cropping domain '%s' from message" % domain)
    return message.replace('.%s' % domain, '')

def send_to_graphite(key, value, domain=None):
    message = "%s %s %s\n" % (key, value, time.time())
    message = remove_domain(message, domain)
    logger.debug("Sending message to Graphite: %s" % message)
    sock = socket.socket()
    sock.connect((CONF.graphite.carbon_server, CONF.graphite.carbon_port))
    sock.sendall(message)
    sock.close()

def send_to_statsd(key, value, domain=None):
    message = "%s %s %s\n" % (key, value, time.time())
    message = remove_domain(message, domain)
    logger.debug("Sending message to Statsd: %s" % message)
    statsd.init_statsd({
        "STATSD_HOST": CONF.graphite.carbon_server,
        "STATSD_BUCKET_PREFIX": CONF.graphite.prefix or ''})
    statsd.gauge(key, value)

def send_to_stdout(key, value, domain=None):
    message = "%s %s %s\n" % (key, value, time.time())
    message = remove_domain(message, domain)
    logger.info("Sending message to stdout: %s" % message)

