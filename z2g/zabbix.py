import logging
import requests

from pyzabbix import ZabbixAPI

logger = logging.getLogger(__name__)

opts = [
    cfg.StrOpt('url',
               default='http://localhost',
               help='Zabbix base URL.'),
    cfg.StrOpt('username',
               default='',
               help='Zabbix login.'),
    cfg.StrOpt('password',
               default='',
               help='Zabbix password.'),
]

CONF = cfg.CONF
CONF.register_opts(opts, group="zabbix")


class ZabbixUtils(object):
    def __init__(self):
        s = requests.Session()
        s.auth = (CONF.zabbix.username, CONF.zabbix.password)
        s.verify = False

        self.zapi = ZabbixAPI(CONF.zabbix.url, s)
        self.zapi.login(CONF.zabbix.username, CONF.zabbix.password)

    def set_graphite_format(self, s):
        """
        Removes whitespaces and lowercases the string
        """
        return ''.join(s.split()).lower()

    def get_hosts_per_hostgroup(self):
        """Returns a dictionary with Zabbix's hostgroup->hosts mapping."""
        d = {}
        for hostgroup in self.zapi.hostgroup.get(real_hosts=1, 
                                                 output="extend",
                                                 selectHosts="extend"):
            name = hostgroup["name"]
            hosts = [host["name"] for host in hostgroup["hosts"]]
            d[name] = hosts
        return d

    def get_items_by_host(self, h, filters=[]):
        """Returns a formated list of (metric, value) pairs.

            h: Zabbix's name for the host.
            filters: a list of keys to search for.
        """
        d = {}
        for f in filters:
            for item in self.zapi.item.get(search={"key_": f},
                                      host=h, 
                                      output=["itemid",
                                              "name", 
                                              "lastvalue", 
                                              "key_"]):
                itemid = item.pop("itemid")
                d[itemid] = item

        l = []
        for m in d.values():
            l.append([m["key_"], m["lastvalue"]])

        l_metric = []
        hostgroups = [group["name"] for group in self.zapi.host.get(
                                            search={"name": h},
                                            output="groups", 
                                            selectGroups="extend")[0]["groups"]]
        h = self.set_graphite_format(h)
        for hgroup in hostgroups:
            hgroup = self.set_graphite_format(hgroup)
            for m in l:
                k = self.set_graphite_format(m[0])
                l_metric.append([".".join([hgroup, h, k]), m[1]])

        return l_metric
