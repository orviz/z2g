import sys
import z2g.config
import z2g.log
import z2g.main

from oslo.config import cfg


CONF = cfg.CONF


def main():
    try:
        z2g.config.parse_args(sys.argv, default_config_files=["/etc/z2g.conf"])
    except cfg.ConfigFilesNotFoundError:
        cfgfile = CONF.config_file[-1] if CONF.config_file else None
        print >> sys.stderr, "Could not find configuration file %s." % cfgfile
        sys.exit(-1)
    z2g.log.setup_logging()

    z2g.main.work()


if __name__ == "__main__":
    main()
